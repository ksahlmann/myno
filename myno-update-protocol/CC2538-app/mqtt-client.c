/*
 * Copyright (c) 2014, Texas Instruments Incorporated - http://www.ti.com/
 * Copyright (c) 2017, George Oikonomou - http://www.spd.gr
 * Copyright (c) 2020, Michael Nowak, Vera Clemens
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 * 3. Neither the name of the copyright holder nor the names of its
 *    contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 * FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE
 * COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
 * SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
 * HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
 * STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 */
/*---------------------------------------------------------------------------*/
#include "contiki.h"
#include "net/routing/routing.h"
#include "mqtt.h"
#include "mqtt-prop.h"
#include "net/ipv6/uip.h"
#include "net/ipv6/uip-icmp6.h"
#include "net/ipv6/sicslowpan.h"
#include "sys/etimer.h"
#include "sys/ctimer.h"
#include "lib/sensors.h"
#include "dev/button-hal.h"
#include "dev/leds.h"
#include "os/sys/log.h"
#include "mqtt-client.h"
#include "cfs/cfs.h"
#include <critical.h>
#include "reg.h"
#include "cpu.h"
#include <stdbool.h>
// Includes for ecc sign and verify
#include "uECC.h"
#include "ontology.h"
#include <stdlib.h>
#include "sha256.h"
#include <stdio.h>
#include <string.h>
#include <strings.h>
#include <stdarg.h>
#include "lzss.h"
#include "Keys.h"

#define MANIFEST_SAVEFILE "savefile"
#define REQID_SAVEFILE "reqFile"

#define SAVE_OFFSET_APP 0
#define SAVE_OFFSET_LOFFSET SAVE_OFFSET_APP+32
#define SAVE_OFFSET_HASH SAVE_OFFSET_LOFFSET+4
#define SAVE_OFFSET_SIZE SAVE_OFFSET_HASH+64
#define SAVE_OFFSET_VERSION SAVE_OFFSET_SIZE+4
#define SAVE_OFFSET_OLD_VERSION SAVE_OFFSET_VERSION+4
#define SAVE_OFFSET_INNER_SIGNATURE SAVE_OFFSET_OLD_VERSION+4
#define SAVE_OFFSET_DEVICE_NONCE SAVE_OFFSET_INNER_SIGNATURE+64
#define SAVE_OFFSET_OUTER_SIGNATURE SAVE_OFFSET_DEVICE_NONCE+4
#define SAVE_OFFSET_PASSED_INNER SAVE_OFFSET_OUTER_SIGNATURE+64
#define SAVE_OFFSET_PASSED_OUTER SAVE_OFFSET_PASSED_INNER+1
#define SAVE_OFFSET_START_VERIFY SAVE_OFFSET_PASSED_OUTER+1
#define SAVE_OFFSET_SEND_UPDATE_COMPLETE  SAVE_OFFSET_START_VERIFY+1
#define SAVE_OFFSET_SEND_SUCCESS SAVE_OFFSET_SEND_UPDATE_COMPLETE+1

/*---------------------------------------------------------------------------*/
#define LOG_MODULE "mqtt-client"
#ifdef MQTT_CLIENT_CONF_LOG_LEVEL
#define LOG_LEVEL MQTT_CLIENT_CONF_LOG_LEVEL
#else
#define LOG_LEVEL LOG_LEVEL_NONE
#endif
/*---------------------------------------------------------------------------*/
/* Controls whether the example will work in IBM Watson IoT platform mode */
#ifdef MQTT_CLIENT_CONF_WITH_IBM_WATSON
#define MQTT_CLIENT_WITH_IBM_WATSON MQTT_CLIENT_CONF_WITH_IBM_WATSON
#else
#define MQTT_CLIENT_WITH_IBM_WATSON 0
#endif
/*---------------------------------------------------------------------------*/
/* MQTT broker address. Ignored in Watson mode */
#ifdef MQTT_CLIENT_CONF_BROKER_IP_ADDR
#define MQTT_CLIENT_BROKER_IP_ADDR MQTT_CLIENT_CONF_BROKER_IP_ADDR
#else
#define MQTT_CLIENT_BROKER_IP_ADDR "fd00::1"
#endif
/*---------------------------------------------------------------------------*/
/*
 * MQTT Org ID.
 *
 * If it equals "quickstart", the client will connect without authentication.
 * In all other cases, the client will connect with authentication mode.
 *
 * In Watson mode, the username will be "use-token-auth". In non-Watson mode
 * the username will be MQTT_CLIENT_USERNAME.
 *
 * In all cases, the password will be MQTT_CLIENT_AUTH_TOKEN.
 */
#ifdef MQTT_CLIENT_CONF_ORG_ID
#define MQTT_CLIENT_ORG_ID MQTT_CLIENT_CONF_ORG_ID
#else
#define MQTT_CLIENT_ORG_ID "quickstart"
#endif
/*---------------------------------------------------------------------------*/
/* MQTT token */
#ifdef MQTT_CLIENT_CONF_AUTH_TOKEN
#define MQTT_CLIENT_AUTH_TOKEN MQTT_CLIENT_CONF_AUTH_TOKEN
#else
#define MQTT_CLIENT_AUTH_TOKEN "AUTHTOKEN"
#endif
/*---------------------------------------------------------------------------*/
#if MQTT_CLIENT_WITH_IBM_WATSON
/* With IBM Watson support */
static const char *broker_ip = "0064:ff9b:0000:0000:0000:0000:b8ac:7cbd";
#define MQTT_CLIENT_USERNAME "use-token-auth"

#else /* MQTT_CLIENT_WITH_IBM_WATSON */
/* Without IBM Watson support. To be used with other brokers, e.g. Mosquitto */
static const char *broker_ip = MQTT_CLIENT_BROKER_IP_ADDR;

#ifdef MQTT_CLIENT_CONF_USERNAME
#define MQTT_CLIENT_USERNAME MQTT_CLIENT_CONF_USERNAME
#else
#define MQTT_CLIENT_USERNAME "use-token-auth"
#endif

#endif /* MQTT_CLIENT_WITH_IBM_WATSON */
/*---------------------------------------------------------------------------*/
#ifdef MQTT_CLIENT_CONF_STATUS_LED
#define MQTT_CLIENT_STATUS_LED MQTT_CLIENT_CONF_STATUS_LED
#else
#define MQTT_CLIENT_STATUS_LED LEDS_GREEN
#endif
/*---------------------------------------------------------------------------*/
#ifdef MQTT_CLIENT_CONF_WITH_EXTENSIONS
#define MQTT_CLIENT_WITH_EXTENSIONS MQTT_CLIENT_CONF_WITH_EXTENSIONS
#else
#define MQTT_CLIENT_WITH_EXTENSIONS 0
#endif
/*---------------------------------------------------------------------------*/
/*
 * A timeout used when waiting for something to happen (e.g. to connect or to
 * disconnect)
 */
#define CONFIG_SEND_WAIT (CLOCK_SECOND * 5)
#define STATE_MACHINE_PERIODIC     (CLOCK_SECOND >> 1)
/*---------------------------------------------------------------------------*/
/* Provide visible feedback via LEDS during various states */
/* When connecting to broker */
#define CONNECTING_LED_DURATION    (CLOCK_SECOND >> 2)

/* Each time we try to publish */
#define PUBLISH_LED_ON_DURATION    (CLOCK_SECOND)
/*---------------------------------------------------------------------------*/
/* Connections and reconnections */
#define RETRY_FOREVER              0xFF
#define RECONNECT_INTERVAL         (CLOCK_SECOND * 2)

/*
 * Number of times to try reconnecting to the broker.
 * Can be a limited number (e.g. 3, 10 etc) or can be set to RETRY_FOREVER
 */
#define RECONNECT_ATTEMPTS         RETRY_FOREVER
#define CONNECTION_STABLE_TIME     (CLOCK_SECOND * 5)
static struct timer connection_life;
static uint8_t connect_attempt;
/*---------------------------------------------------------------------------*/
/* Various states */
static uint8_t state;
#define STATE_INIT            0
#define STATE_REGISTERED      1
#define STATE_CONNECTING      2
#define STATE_CONNECTED       3
#define STATE_PUBLISHING      4
#define STATE_DISCONNECTED    5
#define STATE_ONEM2MREGISTER  6
#define STATE_IDLE            7
#define STATE_CONFIG_ERROR 0xFE
#define STATE_ERROR        0xFF
/*---------------------------------------------------------------------------*/
#define CONFIG_ORG_ID_LEN        32
#define CONFIG_TYPE_ID_LEN       32
#define CONFIG_AUTH_TOKEN_LEN    32
#define CONFIG_EVENT_TYPE_ID_LEN 32
#define CONFIG_CMD_TYPE_LEN       8
#define CONFIG_IP_ADDR_STR_LEN   64
/*---------------------------------------------------------------------------*/
/* A timeout used when waiting to connect to a network */
#define NET_CONNECT_PERIODIC        (CLOCK_SECOND >> 2)
#define NO_NET_LED_DURATION         (NET_CONNECT_PERIODIC >> 1)
/*---------------------------------------------------------------------------*/
/* Default configuration values */
#define DEFAULT_TYPE_ID             "myno-device"
#define DEFAULT_EVENT_TYPE_ID       "status"
#define DEFAULT_SUBSCRIBE_CMD_TYPE  "+"
#define DEFAULT_BROKER_PORT         1883
#define DEFAULT_PUBLISH_INTERVAL    (30 * CLOCK_SECOND)
#define DEFAULT_KEEP_ALIVE_TIMER    60
#define DEFAULT_RSSI_MEAS_INTERVAL  (CLOCK_SECOND * 30)
/*---------------------------------------------------------------------------*/
#define MQTT_CLIENT_SENSOR_NONE     (void *)0xFFFFFFFF
/*---------------------------------------------------------------------------*/
/* Payload length of ICMPv6 echo requests used to measure RSSI with def rt */
#define ECHO_REQ_PAYLOAD_LEN   20
/*---------------------------------------------------------------------------*/
// Buffer for MQTT Messages
static char messagebuffer[600] = {0};
// Manifest Variables 
static char app_id[32] = "";
static uint32_t link_offset = 0;
// TODO: Should be stored in binary form instead
static char hash_update[64] = "";
static uint32_t size = 0;
static uint32_t version = 0;
static uint32_t old_version = 0; 
static uint8_t inner_signature[64] = {};
static uint32_t device_nonce = 0;
static uint8_t outer_signature[64] = {};
// Status variables
bool start_verify = 0;
bool passed_inner = 0;
bool passed_outer = 0;
bool send_update_success = 0;
uint8_t chunks_received = 0;
uint8_t chunks_expected = 0;
int current_slice_no;
int expected_slice_no;

static bool sent_config = 0;
static long remaining_ontology = -1;
static long length_ontology = -1;
static bool end_delimiter_sent = 0;

/* For hash calculation of inner manifest, outer manifest and update image. */
static uint8_t hash[32] = {0};
/* For inner signature. */
// TODO: Should be stored in binary form instead
// TODO: Should not be stored twice (see inner_signature variable)
static char signatureBuffer[129]= {0};
/* For hash of update image. */
SHA256_CTX ctx_image; 

/*---------------------------------------------------------------------------*/
/* MQTTv5 */
#if MQTT_5
/* For sensor values */
static uint8_t PUB_TOPIC_ALIAS;
/* For MUP responses */
static uint8_t RPC_RESPONSE_TOPIC_ALIAS;
static uint8_t SLICES_RESPONSE_TOPIC_ALIAS;

// static bool rpc_response_topic_alias_registered = 0;
static bool slices_response_topic_alias_registered = 0;

struct mqtt_prop_list *slice_response_publish_props;

/* Control whether or not to perform authentication (MQTTv5) */
#define MQTT_5_AUTH_EN 0
#if MQTT_5_AUTH_EN
struct mqtt_prop_list *auth_props;
#endif
#endif
/*---------------------------------------------------------------------------*/

PROCESS_NAME(mqtt_client_process);
AUTOSTART_PROCESSES(&mqtt_client_process);
/*---------------------------------------------------------------------------*/
/**
 * \brief Data structure declaration for the MQTT client configuration
 */
typedef struct mqtt_client_config {
  char org_id[CONFIG_ORG_ID_LEN];
  char type_id[CONFIG_TYPE_ID_LEN];
  char auth_token[CONFIG_AUTH_TOKEN_LEN];
  char event_type_id[CONFIG_EVENT_TYPE_ID_LEN];
  char broker_ip[CONFIG_IP_ADDR_STR_LEN];
  char cmd_type[CONFIG_CMD_TYPE_LEN];
  clock_time_t pub_interval;
  int def_rt_ping_interval;
  uint16_t broker_port;
} mqtt_client_config_t;
/*---------------------------------------------------------------------------*/
/* Maximum TCP segment size for outgoing segments of our socket */
#define MAX_TCP_SEGMENT_SIZE    128
/*---------------------------------------------------------------------------*/
/*
 * Buffers for Client ID and Topic.
 * Make sure they are large enough to hold the entire respective string
 *
 * d:quickstart:status:EUI64 is 32 bytes long
 * iot-2/evt/status/fmt/json is 25 bytes
 * We also need space for the null termination
 */
#define BUFFER_SIZE 64
static char client_id[BUFFER_SIZE];
static char pub_topic[BUFFER_SIZE];

static char reqid_buffer[BUFFER_SIZE];
/*---------------------------------------------------------------------------*/
/*
 * The main MQTT buffers.
 * We will need to increase if we start publishing more data.
 */
#define APP_BUFFER_SIZE 4096
static struct mqtt_connection conn;
static char app_buffer[APP_BUFFER_SIZE];
/*---------------------------------------------------------------------------*/
#define QUICKSTART "quickstart"
/*---------------------------------------------------------------------------*/
static struct mqtt_message *msg_ptr = 0;
static struct etimer publish_periodic_timer;
static struct ctimer publish_led_timer;
static struct ctimer publish_response_timer;

// TODO This feature could not be tested due to time constraints and is therefore deactivated until it can be tested.
// static struct ctimer unsubscribe_from_slice_topic_timer;
// #define UNSUBSCRIBE_TIMER_DURATION    (CLOCK_SECOND) * 60 * 5

static char *buf_ptr;
static uint16_t seq_nr_value = 0;
/*---------------------------------------------------------------------------*/
/* Parent RSSI functionality */
static struct uip_icmp6_echo_reply_notification echo_reply_notification;
static struct etimer echo_request_timer;
static int def_rt_rssi = 0;
/*---------------------------------------------------------------------------*/
static mqtt_client_config_t conf;
/*---------------------------------------------------------------------------*/
#if MQTT_CLIENT_WITH_EXTENSIONS
extern const mqtt_client_extension_t *mqtt_client_extensions[];
extern const uint8_t mqtt_client_extension_count;
#else
static const mqtt_client_extension_t *mqtt_client_extensions[] = { NULL };
static const uint8_t mqtt_client_extension_count = 0;
#endif

/*---------------------------------------------------------------------------*/
PROCESS(mqtt_client_process, "MQTT Client");
/*---------------------------------------------------------------------------*/
static int
ipaddr_sprintf(char *buf, uint8_t buf_len, const uip_ipaddr_t *addr)
{
  uint16_t a;
  uint8_t len = 0;
  int i, f;
  for(i = 0, f = 0; i < sizeof(uip_ipaddr_t); i += 2) {
    a = (addr->u8[i] << 8) + addr->u8[i + 1];
    if(a == 0 && f >= 0) {
      if(f++ == 0) {
        len += snprintf(&buf[len], buf_len - len, "::");
      }
    } else {
      if(f > 0) {
        f = -1;
      } else if(i > 0) {
        len += snprintf(&buf[len], buf_len - len, ":");
      }
      len += snprintf(&buf[len], buf_len - len, "%x", a);
    }
  }

  return len;
}
/*---------------------------------------------------------------------------*/
static void
echo_reply_handler(uip_ipaddr_t *source, uint8_t ttl, uint8_t *data,
                   uint16_t datalen)
{
  if(uip_ip6addr_cmp(source, uip_ds6_defrt_choose())) {
    def_rt_rssi = sicslowpan_get_last_rssi();
  }
}
/*---------------------------------------------------------------------------*/
/**
 * Subscribes to a topic.
 */
static void
subscribe(char* topic)
{
  mqtt_status_t status;

#if MQTT_5
  status = mqtt_subscribe(&conn, NULL, topic, MQTT_QOS_LEVEL_0,
                          MQTT_NL_OFF, MQTT_RAP_OFF, MQTT_RET_H_SEND_ALL,
                          MQTT_PROP_LIST_NONE);
#else
  status = mqtt_subscribe(&conn, NULL, topic, MQTT_QOS_LEVEL_0);
#endif

  if(status == MQTT_STATUS_OK) {
    LOG_INFO("Subscribed to topic %s.\n", topic);
  } else {
    LOG_ERR("Error while subscribing to topic %s: %d\n", topic, status);
  }
}
/*---------------------------------------------------------------------------*/
/**
 * Unsubscribes from a topic.
 */
static void
unsubscribe(char* topic)
{
  mqtt_status_t status;

#if MQTT_5
  status = mqtt_unsubscribe(&conn, NULL, topic, MQTT_PROP_LIST_NONE);
#else
  status = mqtt_unsubscribe(&conn, NULL, topic);
#endif

  if(status == MQTT_STATUS_OK) {
    LOG_INFO("Unsubscribed from topic %s.\n", topic);
  } else {
    LOG_ERR("Error while unsubscribing from topic %s: %d\n", topic, status);
  }
}
/*---------------------------------------------------------------------------*/
static void
publish_led_off(void *d)
{
  leds_off(MQTT_CLIENT_STATUS_LED);
}
/*---------------------------------------------------------------------------*/
/**
 * Sends response on update slices response topic.
 */
#if SEND_UPDATE_SLICE_ACKS
static void
send_mqtt_response (void * response) 
{
  LOG_INFO("Publishing response: topic='%s', response='%s'\n", UPDATE_SLICES_RESPONSE_TOPIC, (char *) response);
	
	snprintf(app_buffer, APP_BUFFER_SIZE-1, "%s", (char *) response);

  if(mqtt_ready(&conn) && conn.out_buffer_sent) {

    mqtt_status_t status = MQTT_STATUS_OK;
#if MQTT_5
    static uint8_t prop_err = 1;
#endif

#if MQTT_5
    /* Only send full topic name with the first PUBLISH
    * Afterwards, only use topic alias
    */
    if(!slices_response_topic_alias_registered) {
      status = mqtt_publish(&conn, NULL, UPDATE_SLICES_RESPONSE_TOPIC, (uint8_t *)app_buffer,
                            strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
                            SLICES_RESPONSE_TOPIC_ALIAS, MQTT_TOPIC_ALIAS_OFF,
                            slice_response_publish_props);
      LOG_DBG("MQTT status: %x\n", status);

      LOG_DBG("Registering slice response topic alias.\n");
      prop_err = mqtt_prop_register(&slice_response_publish_props,
                                    NULL,
                                    MQTT_FHDR_MSG_TYPE_PUBLISH,
                                    MQTT_VHDR_PROP_TOPIC_ALIAS,
                                    SLICES_RESPONSE_TOPIC_ALIAS);
      slices_response_topic_alias_registered = 1;
    } else {
      LOG_DBG("Publishing using slice response topic alias.\n");
      status = mqtt_publish(&conn, NULL, UPDATE_SLICES_RESPONSE_TOPIC, (uint8_t *)app_buffer,
                            strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
                            SLICES_RESPONSE_TOPIC_ALIAS, (mqtt_topic_alias_en_t) !prop_err,
                            slice_response_publish_props);
    }
#else
    status = mqtt_publish(&conn, NULL, UPDATE_SLICES_RESPONSE_TOPIC, (uint8_t *) app_buffer,
                          strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF);
#endif

    LOG_DBG("MQTT status: %x\n", status);

    if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
      LOG_INFO("MQTT queue full, retrying later.\n");
      ctimer_set(&publish_response_timer, CLOCK_SECOND, send_mqtt_response, response);
    } else if(status != MQTT_STATUS_OK) {
      LOG_ERR("Failed to publish response (MQTT status: %x), retrying later.\n", status);
      ctimer_set(&publish_response_timer, CLOCK_SECOND, send_mqtt_response, response);
    }
  } else {
    /*
      * Our publish timer fired, but some MQTT packet is already in flight
      * (either not sent at all, or sent but not fully ACKd).
      *
      * This can mean that we have lost connectivity to our broker or that
      * simply there is some network delay. In both cases, we refuse to
      * trigger a new message and we wait for TCP to either ACK the entire
      * packet after retries, or to timeout and notify us.
      */
    LOG_INFO("Publishing... (MQTT state=%d, q=%u)\n", conn.state,
              conn.out_queue_full);
    ctimer_set(&publish_response_timer, CLOCK_SECOND, send_mqtt_response, response);
  }
}
#endif
/*---------------------------------------------------------------------------*/
/**
 * Sends response on RPC response topic.
 */
static void
send_rpc_response (void * response) 
{
  LOG_INFO("Publishing response: topic='%s', response='%s'\n", UPDATE_RPC_RESPONSE_TOPIC, (char *) response);
	
	snprintf(app_buffer, APP_BUFFER_SIZE-1, "%s;%s", reqid_buffer, (char *) response);

  if(mqtt_ready(&conn) && conn.out_buffer_sent) {

    mqtt_status_t status = MQTT_STATUS_OK;
#if MQTT_5
    // static uint8_t prop_err = 1;
#endif

#if MQTT_5
    status = mqtt_publish(&conn, NULL, UPDATE_RPC_RESPONSE_TOPIC, (uint8_t *)app_buffer,
                          strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
                          RPC_RESPONSE_TOPIC_ALIAS, MQTT_TOPIC_ALIAS_OFF, NULL);
#else
    status = mqtt_publish(&conn, NULL, UPDATE_RPC_RESPONSE_TOPIC, (uint8_t *) app_buffer,
                          strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF);
#endif

    LOG_DBG("MQTT status: %x\n", status);

    if(status == MQTT_STATUS_OUT_QUEUE_FULL) {
      LOG_INFO("MQTT queue full, retrying later.\n");
      ctimer_set(&publish_response_timer, CLOCK_SECOND, send_rpc_response, response);
    } else if(status != MQTT_STATUS_OK) {
      LOG_ERR("Failed to publish response (MQTT status: %x), retrying later.\n", status);
      ctimer_set(&publish_response_timer, CLOCK_SECOND, send_rpc_response, response);
    }
  } else {
    /*
      * Our publish timer fired, but some MQTT packet is already in flight
      * (either not sent at all, or sent but not fully ACKd).
      *
      * This can mean that we have lost connectivity to our broker or that
      * simply there is some network delay. In both cases, we refuse to
      * trigger a new message and we wait for TCP to either ACK the entire
      * packet after retries, or to timeout and notify us.
      */
    LOG_INFO("Publishing... (MQTT state=%d, q=%u)\n", conn.state,
              conn.out_queue_full);
    ctimer_set(&publish_response_timer, CLOCK_SECOND, send_rpc_response, response);
  }
}
/*---------------------------------------------------------------------------*/
/*
 * Sends response determined by return code. Possible values are:
 * 0	=	OK
 * 1	=	NOOP
 * 2	=	ERROR
 * 3	=	MANIFEST-NOT-VALID
 * 4	=	WRONG-APP-ID
 * 5	=	INVALID-NONCE
 * 6	=	OUTER-SIGN-INVALID
 * 7	=	INNER-SIGN-INVALID
 * 8	=	INVALID-VERSIONNR
 * 9	=	SAVESLOT-IN-USE
 * 10	=	IMAGE-TOO-BIG
 * 11	=	IMAGE-INVALID
 * 12 = Device-Token
 * 13 = MANIFEST-SUCCESS
 * 14 = IMAGE-SUCCESS
 */
void send_return_code(int return_code) {
  switch (return_code) {
    case 0:
      send_rpc_response("OK");
      break;
    case 1:
      send_rpc_response("NOOP");
      break;
    case 2:
      send_rpc_response("ERROR");
      break;
    case 3:
      send_rpc_response("MANIFEST-NOT-VALID");
      break;
    case 4:
      send_rpc_response("WRONG-APP-ID");
      break;
    case 5:
      send_rpc_response("INVALID-NONCE");
      break;
    case 6:
      send_rpc_response("OUTER-SIGN-INVALID");
      break;
    case 7:
      send_rpc_response("INNER-SIGN-INVALID");
      break;
    case 8:
      send_rpc_response("INVALID-VERSIONNR");
      break;
    case 9:
      send_rpc_response("SAVESLOT-IN-USE");
      break;
    case 10:
      send_rpc_response("IMAGE-TOO-BIG");
      break;
    case 11:
      send_rpc_response("IMAGE-INVALID");
      break;
    case 12:
      send_rpc_response("123456,1;OK");
      break;
    case 13:
      send_rpc_response("MANIFEST-SUCCESS");
      break;
    case 14:
      send_rpc_response("FIRMWARE-SUCCESS");
      break;
    default:
      send_rpc_response("ERROR");
      break;
  }
}
/*---------------------------------------------------------------------------*/
/**
 * Prints an array of bytes as a hex string to stdout.
 */
void print_hex_string(uint8_t arr[], int len) {
  for(int i = 0; i < len; i++) {
    printf("%02x", arr[i]);
  }
}
/*---------------------------------------------------------------------------*/
/**
 * Writes to a file on disk.
 */
void write_to_file(void* buf, int offset, int len, char* filename) {
  int fd;

  fd = cfs_open(filename, CFS_READ | CFS_WRITE);
  if(fd != -1) {
    cfs_seek(fd, offset, CFS_SEEK_SET);
    int written = cfs_write(fd, buf, len);
    if (written != -1) {
      LOG_DBG("Wrote %d bytes to '%s' at position %d.\n", written, filename, offset);
    } else {
      LOG_ERR("Unable to write to '%s' at position %d.\n", filename, offset);
    }
    cfs_close(fd);
  } else {
    LOG_ERR("Unable to open '%s'.\n", filename);
  }
};
/*---------------------------------------------------------------------------*/
/* 
 * Reads from a file on disk.
 */
void read_from_file(void* buf, int offset, int len, int fd) {
  cfs_seek(fd, offset, CFS_SEEK_SET);
  cfs_read(fd, buf, len);
}
/*---------------------------------------------------------------------------*/
/**
 * Checks inner signature (by vendor) for validity.
 */
void check_inner_signature() {
  snprintf(messagebuffer, sizeof(messagebuffer), "%s;%ld;%.64s;%ld;%ld;%ld", app_id, link_offset, hash_update, size, version, old_version);

  SHA256_CTX ctx;
  sha256_init(&ctx);
  sha256_update(&ctx, (unsigned char*) messagebuffer, strlen(messagebuffer));
  sha256_final(&ctx, hash);

  if (LOG_DBG_ENABLED) {
    LOG_DBG("Verifying inner signature: ");
    print_hex_string(inner_signature, sizeof(inner_signature)/sizeof(inner_signature[0]));
    printf("\n");
    LOG_DBG("Inner manifest is: %s\n", messagebuffer);
    LOG_DBG("SHA256 hash of inner manifest is: ");
    print_hex_string(hash, sizeof(hash)/sizeof(hash[0]));
    printf("\n");
  }
        
  if(!uECC_verify(publicManufacturer, hash, sizeof(hash), inner_signature, uECC_secp256r1())) {
    passed_inner = 0;
    LOG_ERR("Inner signature invalid.\n");
    write_to_file("0", SAVE_OFFSET_PASSED_INNER, sizeof(passed_inner), MANIFEST_SAVEFILE);
  } else {
    passed_inner = 1; 
    LOG_INFO("Inner signature valid.\n");
    write_to_file("1", SAVE_OFFSET_PASSED_INNER, sizeof(passed_inner), MANIFEST_SAVEFILE);
  }
}
/*---------------------------------------------------------------------------*/
/**
 * Checks outer signature (by update server) for validity.
 */
void check_outer_signature(){
  snprintf(messagebuffer, sizeof(messagebuffer), "%s;%ld;%.64s;%ld;%ld;%ld;%s;%ld",
            app_id, link_offset, hash_update, size, 
            version, old_version, signatureBuffer, 
            device_nonce);

  SHA256_CTX ctx;
  sha256_init(&ctx);
  sha256_update(&ctx,  (unsigned char*)  messagebuffer, strlen(messagebuffer));
  sha256_final(&ctx, hash);

  if (LOG_DBG_ENABLED) {
    LOG_DBG("Verifying outer signature: ");
    print_hex_string(outer_signature, sizeof(outer_signature)/sizeof(outer_signature[0]));
    printf("\n");
    LOG_DBG("Outer manifest is: %s\n", messagebuffer);
    LOG_DBG("SHA256 hash of outer manifest is: ");
    print_hex_string(hash, sizeof(hash)/sizeof(hash[0]));
    printf("\n");
  }

  if(!uECC_verify(publicUpdateserver, hash, sizeof(hash), outer_signature, uECC_secp256r1())) {
    passed_outer = 0;
    LOG_ERR("Outer signature invalid.\n");
    write_to_file("0", SAVE_OFFSET_PASSED_OUTER, sizeof(passed_outer), MANIFEST_SAVEFILE);
  } else {
    passed_outer = 1; 
    LOG_INFO("Outer signature valid.\n");
    write_to_file("1", SAVE_OFFSET_PASSED_OUTER, sizeof(passed_outer), MANIFEST_SAVEFILE);
  }
}
/*---------------------------------------------------------------------------*/
/* 
 * Loads manifest parameters from savefile.
 */
void load_manifest_from_savefile() {
  LOG_INFO("Reading state from '%s' and '%s'.\n", MANIFEST_SAVEFILE, REQID_SAVEFILE);
  memset(&messagebuffer, 0, sizeof(messagebuffer));
  int fd = cfs_open(MANIFEST_SAVEFILE, CFS_READ);
  if(fd != -1) {
    read_from_file(app_id, SAVE_OFFSET_APP, sizeof(app_id), fd);
    LOG_DBG("Read app_id=%s\n", app_id);

    read_from_file(&link_offset, SAVE_OFFSET_LOFFSET, sizeof(link_offset), fd);
    LOG_DBG("Read link_offset=%ld\n", link_offset);

    read_from_file(hash_update, SAVE_OFFSET_HASH, sizeof(hash_update), fd);
    LOG_DBG("Read hash_update=%s\n", hash_update);

    read_from_file(&size, SAVE_OFFSET_SIZE, sizeof(size), fd);
    LOG_DBG("Read size=%ld\n", size);

    read_from_file(&version, SAVE_OFFSET_VERSION, sizeof(version), fd);
    LOG_DBG("Read version=%ld\n", version);

    read_from_file(&old_version, SAVE_OFFSET_OLD_VERSION, sizeof(old_version), fd);
    LOG_DBG("Read old_version=%ld\n", old_version);

    read_from_file(inner_signature, SAVE_OFFSET_INNER_SIGNATURE, sizeof(inner_signature), fd);
    LOG_DBG("Read inner_signature=");
    if(LOG_DBG_ENABLED) {
      print_hex_string(inner_signature, 64);
      printf("\n");
    }

    read_from_file(&device_nonce, SAVE_OFFSET_DEVICE_NONCE, sizeof(device_nonce), fd);
    LOG_DBG("Read device_nonce=%ld\n", device_nonce);

    read_from_file(outer_signature, SAVE_OFFSET_OUTER_SIGNATURE, sizeof(outer_signature), fd);
    LOG_DBG("Read outer_signature=");
    if(LOG_DBG_ENABLED) {
      print_hex_string(outer_signature, 64);
      printf("\n");
    }

    read_from_file(&passed_inner, SAVE_OFFSET_PASSED_INNER, sizeof(passed_inner), fd);
    LOG_DBG("Read passed_inner=%d\n", passed_inner);

    read_from_file(&passed_outer, SAVE_OFFSET_PASSED_OUTER, sizeof(passed_outer), fd);
    LOG_DBG("Read passed_outer=%d\n", passed_outer);

    read_from_file(&start_verify, SAVE_OFFSET_START_VERIFY, sizeof(start_verify), fd);
    LOG_DBG("Read start_verify=%d\n", start_verify);

    read_from_file(&send_update_success, SAVE_OFFSET_SEND_SUCCESS, sizeof(send_update_success), fd);
    LOG_DBG("Read send_update_success=%d\n", send_update_success);

    cfs_close(fd);
  } else {
    LOG_ERR("Unable to open '%s'.\n", MANIFEST_SAVEFILE);
  }

  fd = cfs_open(REQID_SAVEFILE, CFS_READ);
  if(fd != -1) {
    read_from_file(reqid_buffer, 0, sizeof(reqid_buffer), fd);
    LOG_DBG("Read reqid_buffer=%s\n", reqid_buffer);
    cfs_close(fd);
  } else {
    LOG_ERR("Unable to open '%s'.\n", REQID_SAVEFILE);
  }
}
/*---------------------------------------------------------------------------*/
/* 
 * Reacts to published messages on MUP control topics:
 * 
 * - "yang/update/DEVICEUUID": Device nonce requests and update manifests.
 * - "yang/update/image/DEVICEUUID": Firmware images.
 */
static void
pub_handler(const char *topic, uint16_t topic_len, uint16_t payload_len,
            const uint8_t *chunk, uint16_t chunk_len, uint8_t first_chunk)
{
  LOG_INFO("Pub Handler: topic='%s' (len=%u), chunk_len=%u", topic, topic_len, chunk_len);

  int return_code = 2;

  if(strncmp(topic, UPDATE_SLICES_TOPIC, strlen(UPDATE_SLICES_TOPIC)) == 0) {
    char* slice;
    int slice_len;

    if(first_chunk == 1) {
      current_slice_no = atoi((char*) chunk);
    }
    if(current_slice_no != expected_slice_no) {
#if SEND_UPDATE_SLICE_ACKS
      LOG_INFO("\n");
      LOG_ERR("Received slice number %d but expected %d. Re-sending ACK.\n", current_slice_no, expected_slice_no);
      char response[8];
      sprintf(response, "%d,%s", expected_slice_no-1, UPDATE_SLICE_ACK);
      send_mqtt_response(response);
#endif
      return;
    }

    if(first_chunk == 1) {
      // Separate slice no. and actual slice (separated by comma)
      slice = strchr((char*) chunk, ',')+1;
      int slice_no_len = (int) (slice - (char *) chunk);
      slice_len = chunk_len - slice_no_len;

      chunks_expected = payload_len/chunk_len + (payload_len % chunk_len != 0);
      chunks_received = 1;
    } else {
      slice = (char*) chunk;
      slice_len = chunk_len;

      chunks_received += 1;
    }

    if(LOG_INFO_ENABLED) {
      if(first_chunk == 1) {
        printf(", chunk='%d,", current_slice_no);
      } else {
        printf(", chunk='");
      }
      print_hex_string((uint8_t*) slice, slice_len);
      printf("'\n");
    }
    LOG_INFO("Expecting %d chunks.\n", chunks_expected);

    // Update SHA256 hash
    sha256_update(&ctx_image, (unsigned char*) slice, slice_len);

    if(chunks_received == chunks_expected) {
#if SEND_UPDATE_SLICE_ACKS
      char response[8];
      sprintf(response, "%d,%s", current_slice_no, UPDATE_SLICE_ACK);
      send_mqtt_response(response);
#endif
      expected_slice_no = current_slice_no + 1;
    }
  } else if(strncmp(topic, UPDATE_RPC_TOPIC, strlen(UPDATE_RPC_TOPIC)) == 0) {
    if(LOG_INFO_ENABLED) {
      printf(", chunk='%s'\n", chunk);
    }

    // Read request ID
    char* semicolon_pos = strchr((char*) chunk, ';');
    int reqid_len = (int) (semicolon_pos - (char *) chunk);
    snprintf(reqid_buffer, reqid_len+1, "%s", chunk);
    
    /* GET-DEVICE-TOKEN */
    if(strncmp(semicolon_pos+1, CTRL_TOKEN_CMD, strlen(CTRL_TOKEN_CMD)) == 0) {
      return_code = 12;
    }
    /* PUB-UPDATE-MANIFEST */
    else if(strncmp(semicolon_pos+1, CTRL_MANIFEST_CMD, strlen(CTRL_MANIFEST_CMD)) == 0) {
      // Get message sent with command
      snprintf(messagebuffer, sizeof(messagebuffer)-1, "%s", chunk+reqid_len+strlen(CTRL_MANIFEST_CMD)+2);

      // Separate message into manifest key and value
      int index_comma = (int) (strchr((char*) messagebuffer, ',') - (char *)messagebuffer);
      int manifest_key = -1;
      char cast_buffer[8];
      snprintf(cast_buffer, index_comma+1, "%s",  messagebuffer);
      manifest_key = strtol(cast_buffer, NULL, 10);
      char* manifest_value = messagebuffer+index_comma+1;

      /**
       * For some reason, the board gets stuck after receiving the first part of the firmware image if this code is deleted.
       * MYSTERIOUS CODE BEGIN
       */
      int fd;
      char buf[256];
      /* MYSTERIOUS CODE END */

      switch(manifest_key) {
        // app_id
        case 0:
          sprintf(app_id, manifest_value, sizeof(app_id));
          LOG_INFO("Received part of manifest: app_id=%s\n", app_id);
          write_to_file(app_id, SAVE_OFFSET_APP, sizeof(app_id), MANIFEST_SAVEFILE);
          break;
        // link_offset
        case 1:
          link_offset = strtol(manifest_value, NULL, 10);
          LOG_INFO("Received part of manifest: link_offset=%ld\n", link_offset);
          write_to_file(&link_offset, SAVE_OFFSET_LOFFSET, sizeof(link_offset), MANIFEST_SAVEFILE);
          break;
        // hash_update
        case 2: 
          sprintf(hash_update, manifest_value, strlen(manifest_value)+1);
          // hash_update[strlen(manifest_value)+2] = 0;
          LOG_INFO("Received part of manifest: hash_update=%.64s\n", hash_update);
          write_to_file(hash_update, SAVE_OFFSET_HASH, sizeof(hash_update), MANIFEST_SAVEFILE);
          break;
        // size
        case 3:
          size = strtol(manifest_value, NULL, 10);
          LOG_INFO("Received part of manifest: size=%ld\n", size);
          write_to_file(&size, SAVE_OFFSET_SIZE, sizeof(size), MANIFEST_SAVEFILE);
          break;
        // version
        case 4:
          version = strtol(manifest_value, NULL, 10);
          LOG_INFO("Received part of manifest: version=%ld\n", version);
          write_to_file(&version, SAVE_OFFSET_VERSION, sizeof(version), MANIFEST_SAVEFILE);
          break;
        // old_version
        case 5:
          old_version = strtol(manifest_value, NULL, 10);
          LOG_INFO("Received part of manifest: old_version=%ld\n", old_version);
          write_to_file(&old_version, SAVE_OFFSET_OLD_VERSION, sizeof(old_version), MANIFEST_SAVEFILE);
          break;
        // innerSignature
        case 6:
          for (uint8_t i = 0; i < strlen(manifest_value)/2+1; i++) {
            inner_signature[i] = 0;
            for (uint8_t j = 0; j < 2; j++) {
              char first_char = manifest_value[(i*2)+j];
              if (first_char >= '0' && first_char <= '9') {
                inner_signature[i] = inner_signature[i]*16 + first_char - '0';
              } else if (first_char >= 'A' && first_char <= 'F') {
                inner_signature[i] = inner_signature[i]*16 + first_char - 'A' + 10;
              } else if (first_char >= 'a' && first_char <= 'f') {
                inner_signature[i] = inner_signature[i]*16 + first_char - 'a' + 10;
              }
            }
          }
          if (LOG_INFO_ENABLED) {
            LOG_INFO("Received part of manifest: innerSignature=");
            print_hex_string(inner_signature, 64);
            printf("\n");
          }
          write_to_file(inner_signature, SAVE_OFFSET_INNER_SIGNATURE, sizeof(inner_signature), MANIFEST_SAVEFILE);
          strncpy(signatureBuffer, manifest_value, sizeof(signatureBuffer));
          printf("inner signature (signatureBuffer): %s\n", signatureBuffer);
          break;
        // device_nonce
        case 7:
          device_nonce = strtol(manifest_value, NULL, 10);
          LOG_INFO("Received part of manifest: device_nonce=%ld\n", device_nonce);
          write_to_file(&device_nonce, SAVE_OFFSET_DEVICE_NONCE, sizeof(device_nonce), MANIFEST_SAVEFILE);
          break;
        // outer_signature
        case 8:
          for (uint8_t i = 0; i < strlen(manifest_value)/2+1; i++) {
            outer_signature[i] = 0;
            for (uint8_t j = 0; j < 2; j++) {
              char firstchar = manifest_value[(i*2)+j];
              if (firstchar >= '0' && firstchar <= '9') {
                  outer_signature[i] = outer_signature[i]*16 + firstchar - '0';
              } else if (firstchar >= 'A' && firstchar <= 'F') {
                  outer_signature[i] = outer_signature[i]*16 + firstchar - 'A' + 10;
              } else if (firstchar >= 'a' && firstchar <= 'f') {
                  outer_signature[i] = outer_signature[i]*16 + firstchar - 'a' + 10;
              } 
            }
          }
          if (LOG_INFO_ENABLED) {
            LOG_INFO("Received part of manifest: outer_signature=");
            print_hex_string(outer_signature, 64);
            printf("\n");
          }
          write_to_file(outer_signature, SAVE_OFFSET_OUTER_SIGNATURE, sizeof(outer_signature), MANIFEST_SAVEFILE);
          break;
        case 9:
          start_verify = 1;
          LOG_INFO("Received end delimiter of manifest.\n");
          /**
           * For some reason, the board gets stuck if this code is deleted.
           * MYSTERIOUS CODE BEGIN
           */
          fd = cfs_open(MANIFEST_SAVEFILE, CFS_READ | CFS_WRITE);
          if(fd >= 0) {
            cfs_seek(fd, SAVE_OFFSET_START_VERIFY, CFS_SEEK_SET);
            cfs_read(fd, buf, 256);
            cfs_close(fd);
          }
          /* MYSTERIOUS CODE END */
          cfs_remove(REQID_SAVEFILE);
          write_to_file(reqid_buffer, 0, sizeof(reqid_buffer), REQID_SAVEFILE);
          load_manifest_from_savefile();
          check_inner_signature();
          check_outer_signature();
          if(passed_inner == 1 && passed_outer == 1) {
            return_code = 13;
            subscribe(UPDATE_SLICES_TOPIC);
            // TODO This feature could not be tested due to time constraints and is therefore deactivated until it can be tested.
            // ctimer_set(&unsubscribe_from_slice_topic_timer, UNSUBSCRIBE_TIMER_DURATION, unsubscribe, UPDATE_SLICES_TOPIC);
            expected_slice_no = 0;
          }
          cfs_remove(MANIFEST_SAVEFILE);
          break;
      }
      if(return_code != 13) {
        return_code = 0;
      }
    }
    /* PUB-UPDATE-IMAGE */
    else if(strncmp(semicolon_pos+1, CTRL_FIRMWARE_CMD, strlen(CTRL_FIRMWARE_CMD)) == 0) {
      // Get message sent with command
      snprintf(messagebuffer, sizeof(messagebuffer), "%s", chunk+reqid_len+strlen(CTRL_FIRMWARE_CMD)+2);
      LOG_DBG("Received message: %s\n", messagebuffer);
      if(strcmp(messagebuffer, "FIN") == 0) {
        LOG_INFO("Received FIN command for firmware upload.\n");
        unsubscribe(UPDATE_SLICES_TOPIC);

        sha256_final(&ctx_image, hash);

        if(LOG_DBG_ENABLED) {
          LOG_DBG("Comparing computed hash to manifest hash.\n");
          LOG_DBG("Computed hash is: ");
          print_hex_string(hash, sizeof(hash)/sizeof(hash[0]));
          printf("\n");
          LOG_DBG("Manifest hash is: %.64s\n", hash_update);
        }

        // TODO This conversion could be removed if the manifest hash was stored in binary form
        static char hash_string[64] = {0};
        for(int i = 0; i < 32; i++) {
          snprintf(&hash_string[i*2], 3, "%02x", hash[i]);
        }
        return_code = (strncmp(hash_string, hash_update, 64) == 0) ? 14 : 2;

        sha256_init(&ctx_image);
      } else {
        LOG_INFO("Received unknown command: %s\n", messagebuffer);
      }
    }
    send_return_code(return_code);
  }

  memset(&messagebuffer, 0, sizeof(messagebuffer));
  return;
}
/*---------------------------------------------------------------------------*/
static void
mqtt_event(struct mqtt_connection *m, mqtt_event_t event, void *data)
{
  switch(event) {
  case MQTT_EVENT_CONNECTED: {
    LOG_INFO("Application has a MQTT connection. MQTT version: %d\n", MQTT_PROTOCOL_VERSION);
    timer_set(&connection_life, CONNECTION_STABLE_TIME);
    state = STATE_CONNECTED;
    break;
  }
  case MQTT_EVENT_DISCONNECTED:
  case MQTT_EVENT_CONNECTION_REFUSED_ERROR: {
    LOG_ERR("MQTT Disconnect. Reason %u\n", *((mqtt_event_t *)data));

#if MQTT_5
    slices_response_topic_alias_registered = 0;
#endif

    state = STATE_DISCONNECTED;
    process_poll(&mqtt_client_process);
    break;
  }
  case MQTT_EVENT_PUBLISH: {
    msg_ptr = data;

#if MQTT_5
    if(msg_ptr->first_chunk) {
      /* 
      * Remove property bytes from payload length
      * (Properties are considered to be part of the "payload" by Contiki-NG)
      * See: https://github.com/contiki-ng/contiki-ng/issues/1341
      */
      msg_ptr->payload_length -= m->in_packet.properties_enc_len + m->in_packet.properties_len;
    }
#endif

    if(msg_ptr->first_chunk) {
      LOG_INFO("Application received publish for topic '%s'. Payload "
               "size is %i bytes.\n", msg_ptr->topic, msg_ptr->payload_length);
    }
    LOG_INFO("Chunk size is %i bytes. First chunk: %i\n", msg_ptr->payload_chunk_length,
             msg_ptr->first_chunk);

    pub_handler(msg_ptr->topic, strlen(msg_ptr->topic), msg_ptr->payload_length,
                msg_ptr->payload_chunk, msg_ptr->payload_chunk_length,
                msg_ptr->first_chunk);

#if MQTT_5
    /* Print any properties received along with the message */
    mqtt_prop_print_input_props(m);
#endif
    break;
  }
  case MQTT_EVENT_SUBACK: {
#if MQTT_31
    LOG_DBG("Application is subscribed to topic successfully\n");
#else
    struct mqtt_suback_event *suback_event = (struct mqtt_suback_event *)data;

    if(suback_event->success) {
      LOG_INFO("Application is subscribed to topic successfully.\n");
    } else {
      LOG_ERR("Application failed to subscribe to topic (ret code %x).\n", suback_event->return_code);
    }
#if MQTT_5
    /* Print any properties received along with the message */
    mqtt_prop_print_input_props(m);
#endif
#endif
    break;
  }
  case MQTT_EVENT_UNSUBACK: {
    LOG_INFO("Application is unsubscribed to topic successfully.\n");
    break;
  }
  case MQTT_EVENT_PUBACK: {
    LOG_INFO("Publish acknowledged.\n");
    break;
  }
#if MQTT_5_AUTH_EN
  case MQTT_EVENT_AUTH: {
    LOG_DBG("Continuing auth.\n");
    struct mqtt_prop_auth_event *auth_event = (struct mqtt_prop_auth_event *)data;
    break;
  }
#endif
  default:
    LOG_INFO("Application got a unhandled MQTT event: %i\n", event);
    break;
  }
}
/*---------------------------------------------------------------------------*/
static int
construct_pub_topic(void)
{
  int len = snprintf(pub_topic, BUFFER_SIZE, "iot-2/evt/%s/fmt/json",
                     conf.event_type_id);

  /* len < 0: Error. Len >= BUFFER_SIZE: Buffer too small */
  if(len < 0 || len >= BUFFER_SIZE) {
    LOG_INFO("Pub Topic: %d, Buffer %d\n", len, BUFFER_SIZE);
    return 0;
  }

#if MQTT_5
  PUB_TOPIC_ALIAS = 1;
  RPC_RESPONSE_TOPIC_ALIAS = 2;
  SLICES_RESPONSE_TOPIC_ALIAS = 3;
#endif

  return 1;
}
/*---------------------------------------------------------------------------*/
static int
construct_client_id(void)
{
  int len = snprintf(client_id, BUFFER_SIZE, "d:%s:%s:%02x%02x%02x%02x%02x%02x",
                     conf.org_id, conf.type_id,
                     linkaddr_node_addr.u8[0], linkaddr_node_addr.u8[1],
                     linkaddr_node_addr.u8[2], linkaddr_node_addr.u8[5],
                     linkaddr_node_addr.u8[6], linkaddr_node_addr.u8[7]);

  /* len < 0: Error. Len >= BUFFER_SIZE: Buffer too small */
  if(len < 0 || len >= BUFFER_SIZE) {
    LOG_ERR("Client ID: %d, Buffer %d\n", len, BUFFER_SIZE);
    return 0;
  }

  return 1;
}
/*---------------------------------------------------------------------------*/
static void
update_config(void)
{
  if(construct_client_id() == 0) {
    /* Fatal error. Client ID larger than the buffer */
    state = STATE_CONFIG_ERROR;
    return;
  }

  if(construct_pub_topic() == 0) {
    /* Fatal error. Topic larger than the buffer */
    state = STATE_CONFIG_ERROR;
    return;
  }

  /* Reset the counter */
  seq_nr_value = 0;

  state = STATE_INIT;

  /*
   * Schedule next timer event ASAP
   *
   * If we entered an error state then we won't do anything when it fires.
   *
   * Since the error at this stage is a config error, we will only exit this
   * error state if we get a new config.
   */
  etimer_set(&publish_periodic_timer, 0);

#if MQTT_5
  LIST_STRUCT_INIT(&(conn.will), properties);

  mqtt_props_init();
#endif

  return;
}
/*---------------------------------------------------------------------------*/
static int
init_config()
{
  /* Populate configuration with default values */
  memset(&conf, 0, sizeof(mqtt_client_config_t));

  memcpy(conf.org_id, MQTT_CLIENT_ORG_ID, strlen(MQTT_CLIENT_ORG_ID));
  memcpy(conf.type_id, DEFAULT_TYPE_ID, strlen(DEFAULT_TYPE_ID));
  memcpy(conf.auth_token, MQTT_CLIENT_AUTH_TOKEN,
         strlen(MQTT_CLIENT_AUTH_TOKEN));
  memcpy(conf.event_type_id, DEFAULT_EVENT_TYPE_ID,
         strlen(DEFAULT_EVENT_TYPE_ID));
  memcpy(conf.broker_ip, broker_ip, strlen(broker_ip));
  memcpy(conf.cmd_type, DEFAULT_SUBSCRIBE_CMD_TYPE, 1);

  conf.broker_port = DEFAULT_BROKER_PORT;
  conf.pub_interval = DEFAULT_PUBLISH_INTERVAL;
  conf.def_rt_ping_interval = DEFAULT_RSSI_MEAS_INTERVAL;

  return 1;
}
/*---------------------------------------------------------------------------*/
/**
 * Publishes sensor values.
 */
static void
publish(void)
{
  /* Publish MQTT topic in IBM quickstart format */
  int len;
  int remaining = APP_BUFFER_SIZE;
  int i;
  char def_rt_str[64];

  seq_nr_value++;

  buf_ptr = app_buffer;

  len = snprintf(buf_ptr, remaining,
                 "{"
                 "\"d\":{"
                 "\"Platform\":\""CONTIKI_TARGET_STRING"\","
#ifdef CONTIKI_BOARD_STRING
                 "\"Board\":\""CONTIKI_BOARD_STRING"\","
#endif
                 "\"Seq #\":%d,"
                 "\"Uptime (sec)\":%lu",
                 seq_nr_value, clock_seconds());

  if(len < 0 || len >= remaining) {
    LOG_ERR("Buffer too short. Have %d, need %d + \\0\n", remaining,
            len);
    return;
  }

  remaining -= len;
  buf_ptr += len;

  /* Put our Default route's string representation in a buffer */
  memset(def_rt_str, 0, sizeof(def_rt_str));
  ipaddr_sprintf(def_rt_str, sizeof(def_rt_str), uip_ds6_defrt_choose());

  len = snprintf(buf_ptr, remaining,
                 ",\"Def Route\":\"%s\",\"RSSI (dBm)\":%d",
                 def_rt_str, def_rt_rssi);

  if(len < 0 || len >= remaining) {
    LOG_ERR("Buffer too short. Have %d, need %d + \\0\n", remaining,
            len);
    return;
  }
  remaining -= len;
  buf_ptr += len;

  for(i = 0; i < mqtt_client_extension_count; i++) {
    len = snprintf(buf_ptr, remaining, ",%s",
                   mqtt_client_extensions[i]->value());

    if(len < 0 || len >= remaining) {
      LOG_ERR("Buffer too short. Have %d, need %d + \\0\n", remaining,
              len);
      return;
    }
    remaining -= len;
    buf_ptr += len;
  }

  len = snprintf(buf_ptr, remaining, "}}");

  if(len < 0 || len >= remaining) {
    LOG_ERR("Buffer too short. Have %d, need %d + \\0\n", remaining,
            len);
    return;
  }

#if MQTT_5
  /* 
   * Do not use topic alias for sensor values
   */
  mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer,
                strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
                PUB_TOPIC_ALIAS, MQTT_TOPIC_ALIAS_OFF, NULL);
#else
  mqtt_publish(&conn, NULL, pub_topic, (uint8_t *)app_buffer,
               strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF);
#endif

  printf("Publish!\n");
}
/*---------------------------------------------------------------------------*/
static void
connect_to_broker(void)
{
  /* Connect to MQTT server */
  mqtt_connect(&conn, conf.broker_ip, conf.broker_port,
               (conf.pub_interval * 3) / CLOCK_SECOND,
#if MQTT_5
               MQTT_CLEAN_SESSION_ON,
               MQTT_PROP_LIST_NONE);
#else
               MQTT_CLEAN_SESSION_ON);
#endif

  state = STATE_CONNECTING;
}
/*---------------------------------------------------------------------------*/
#if MQTT_5_AUTH_EN
static void
send_auth(struct mqtt_prop_auth_event *auth_info, mqtt_auth_type_t auth_type)
{
  mqtt_prop_clear_prop_list(&auth_props);

  if(auth_info->auth_method.length) {
    (void)mqtt_prop_register(&auth_props,
                             NULL,
                             MQTT_FHDR_MSG_TYPE_AUTH,
                             MQTT_VHDR_PROP_AUTH_METHOD,
                             auth_info->auth_method.string);
  }

  if(auth_info->auth_data.len) {
    (void)mqtt_prop_register(&auth_props,
                             NULL,
                             MQTT_FHDR_MSG_TYPE_AUTH,
                             MQTT_VHDR_PROP_AUTH_DATA,
                             auth_info->auth_data.data,
                             auth_info->auth_data.len);
  }

  /* Connect to MQTT server */
  mqtt_auth(&conn, auth_type, auth_props);

  if(state != STATE_CONNECTING) {
    LOG_DBG("MQTT reauthenticating\n");
  }
}
#endif
/*---------------------------------------------------------------------------*/
static void
ping_parent(void)
{
  if(uip_ds6_get_global(ADDR_PREFERRED) == NULL) {
    return;
  }

  uip_icmp6_send(uip_ds6_defrt_choose(), ICMP6_ECHO_REQUEST, 0,
                 ECHO_REQ_PAYLOAD_LEN);
}
/*---------------------------------------------------------------------------*/
/**
 * Publishes device ontology.
 */
static void
send_oneM2M_definition(void)
{
	int len;
	
	if (end_delimiter_sent) {
		sent_config = 1;
    publish_led_off(NULL);
		return;
	}
	
	if(conn.out_queue_full) {
		LOG_INFO("MQTT queue full, retrying later.\n");
		return;
	}

	if (remaining_ontology > 1) {
    leds_on(MQTT_CLIENT_STATUS_LED);
		len = snprintf(app_buffer, APP_BUFFER_SIZE-1,"%s;%s", 
                DEVICE_UUID, &ontology[length_ontology-remaining_ontology]);
		
		if (len > APP_BUFFER_SIZE-1)
			len = APP_BUFFER_SIZE-1;
		
		len -= strlen(DEVICE_UUID);

    if(mqtt_ready(&conn) && conn.out_buffer_sent) {
		  LOG_INFO("Publishing partial ontology.\n");
      leds_on(MQTT_CLIENT_STATUS_LED);
      ctimer_set(&publish_led_timer, PUBLISH_LED_ON_DURATION, publish_led_off, NULL);

#if MQTT_5
      /* 
       * Do not use topic alias for ontology (yet)
       */
      mqtt_publish(&conn, NULL, CONFIG_TOPIC, (uint8_t *)app_buffer,
                  strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
                  PUB_TOPIC_ALIAS, MQTT_TOPIC_ALIAS_OFF, NULL);
#else
      mqtt_publish(&conn, NULL, CONFIG_TOPIC, (uint8_t *)app_buffer,
                  strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF);
#endif

      remaining_ontology -= len-2;
      LOG_DBG("Remaining ontology: %ld bytes\n", remaining_ontology);
      return;
    } else {
      /*
       * Our publish timer fired, but some MQTT packet is already in flight
       * (either not sent at all, or sent but not fully ACKd).
       *
       * This can mean that we have lost connectivity to our broker or that
       * simply there is some network delay. In both cases, we refuse to
       * trigger a new message and we wait for TCP to either ACK the entire
       * packet after retries, or to timeout and notify us.
       */
      LOG_INFO("Publishing... (MQTT state=%d, q=%u)\n", conn.state,
               conn.out_queue_full);
      return;
    }
	} 
	
	LOG_INFO("Ontology fully published.\n");

  /* Send end message */
	snprintf(app_buffer,APP_BUFFER_SIZE-1,"%s;END",DEVICE_UUID);

#if MQTT_5
      /*
       * Do not use topic alias for ontology (yet)
       */
	mqtt_publish(&conn, NULL, CONFIG_TOPIC, (uint8_t *)app_buffer,
		          strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF,
              PUB_TOPIC_ALIAS, MQTT_TOPIC_ALIAS_OFF, NULL);
#else
	mqtt_publish(&conn, NULL, CONFIG_TOPIC, (uint8_t *)app_buffer,
		          strlen(app_buffer), MQTT_QOS_LEVEL_0, MQTT_RETAIN_OFF);
#endif
		
	end_delimiter_sent = 1;
}
/*---------------------------------------------------------------------------*/
static void
state_machine(void)
{
  switch(state) {
  case STATE_INIT:
    /* If we have just been configured register MQTT connection */
    mqtt_register(&conn, &mqtt_client_process, client_id, mqtt_event,
                  MAX_TCP_SEGMENT_SIZE);

    /*
     * If we are not using the quickstart service (thus we are an IBM
     * registered device), we need to provide user name and password
     */
    if(strncasecmp(conf.org_id, QUICKSTART, strlen(conf.org_id)) != 0) {
      if(strlen(conf.auth_token) == 0) {
        LOG_ERR("User name set, but empty auth token\n");
        state = STATE_ERROR;
        break;
      } else {
        mqtt_set_username_password(&conn, MQTT_CLIENT_USERNAME,
                                   conf.auth_token);
      }
    }

    /* _register() will set auto_reconnect. We don't want that. */
    conn.auto_reconnect = 0;
    connect_attempt = 1;

#if MQTT_5
    mqtt_prop_create_list(&slice_response_publish_props);
    mqtt_prop_print_list(slice_response_publish_props, MQTT_VHDR_PROP_ANY);
#endif

    state = STATE_REGISTERED;
    LOG_DBG("Init MQTT version %d\n", MQTT_PROTOCOL_VERSION);
    /* Continue */
  case STATE_REGISTERED:
    if(uip_ds6_get_global(ADDR_PREFERRED) != NULL) {
      /* Registered and with a public IP. Connect */
      LOG_DBG("Registered. Connect attempt %u\n", connect_attempt);
      ping_parent();
      connect_to_broker();
    } else {
      leds_on(MQTT_CLIENT_STATUS_LED);
      ctimer_set(&publish_led_timer, NO_NET_LED_DURATION, publish_led_off, NULL);
    }
    etimer_set(&publish_periodic_timer, NET_CONNECT_PERIODIC);
    return;
    break;
  case STATE_CONNECTING:
    leds_on(MQTT_CLIENT_STATUS_LED);
    ctimer_set(&publish_led_timer, CONNECTING_LED_DURATION, publish_led_off, NULL);
    /* Not connected yet. Wait */
    LOG_DBG("Connecting (%u)\n", connect_attempt);
    break;
  case STATE_CONNECTED:
    subscribe(UPDATE_RPC_TOPIC);
    state = STATE_ONEM2MREGISTER;
    /* Continue */
  case STATE_ONEM2MREGISTER:
    /* Send ontology to broker */
    if(!sent_config) {
      if(remaining_ontology == -1) {
        LOG_INFO("Starting to send ontology.\n");
        remaining_ontology = strlen(ontology);
        length_ontology = remaining_ontology;
      }
      send_oneM2M_definition();
      etimer_set(&publish_periodic_timer, CONFIG_SEND_WAIT);
      return;
    }
    // We currently do not want to publish sensor values
    // state = STATE_PUBLISHING;
    state = STATE_IDLE;
    break;
  case STATE_IDLE:
    break;
  case STATE_PUBLISHING:
    /* If the timer expired, the connection is stable. */
    if(timer_expired(&connection_life)) {
      /*
       * Intentionally using 0 here instead of 1: We want RECONNECT_ATTEMPTS
       * attempts if we disconnect after a successful connect
       */
      connect_attempt = 0;
    }

    if(mqtt_ready(&conn) && conn.out_buffer_sent) {
      /* Connected. Publish */
      leds_on(MQTT_CLIENT_STATUS_LED);
      ctimer_set(&publish_led_timer, PUBLISH_LED_ON_DURATION, publish_led_off, NULL);
      LOG_INFO("Publishing sensor values.\n");
      publish();
      etimer_set(&publish_periodic_timer, conf.pub_interval);
      /* Return here so we don't end up rescheduling the timer */
      return;
    } else {
      /*
       * Our publish timer fired, but some MQTT packet is already in flight
       * (either not sent at all, or sent but not fully ACKd).
       *
       * This can mean that we have lost connectivity to our broker or that
       * simply there is some network delay. In both cases, we refuse to
       * trigger a new message and we wait for TCP to either ACK the entire
       * packet after retries, or to timeout and notify us.
       */
      LOG_INFO("Publishing... (MQTT state=%d, q=%u)\n", conn.state,
               conn.out_queue_full);
    }
    break;
  case STATE_DISCONNECTED:
    printf("Disconnected\n");
    if(connect_attempt < RECONNECT_ATTEMPTS ||
       RECONNECT_ATTEMPTS == RETRY_FOREVER) {
      /* Disconnect and backoff */
      clock_time_t interval;
#if MQTT_5
      mqtt_disconnect(&conn, MQTT_PROP_LIST_NONE);
#else
      mqtt_disconnect(&conn);
#endif
      connect_attempt++;

      interval = connect_attempt < 3 ? RECONNECT_INTERVAL << connect_attempt :
        RECONNECT_INTERVAL << 3;

      printf("Disconnected. Attempt %u in %lu ticks\n", connect_attempt, interval);

      etimer_set(&publish_periodic_timer, interval);

      state = STATE_REGISTERED;
      return;
    } else {
      /* Max reconnect attempts reached. Enter error state */
      state = STATE_ERROR;
      printf("Aborting connection after %u attempts\n", connect_attempt - 1);
    }
    break;
  case STATE_CONFIG_ERROR:
    /* Idle away. The only way out is a new config */
    LOG_ERR("Bad configuration.\n");
    return;
  case STATE_ERROR:
  default:
    leds_on(MQTT_CLIENT_STATUS_LED);
    /*
     * 'default' should never happen.
     *
     * If we enter here it's because of some error. Stop timers. The only thing
     * that can bring us out is a new config event
     */
    LOG_ERR("Default case: State=0x%02x\n", state);
    return;
  }

  /* If we didn't return so far, reschedule ourselves */
  etimer_set(&publish_periodic_timer, STATE_MACHINE_PERIODIC);
}
/*---------------------------------------------------------------------------*/
static void
init_extensions(void)
{
  int i;

  for(i = 0; i < mqtt_client_extension_count; i++) {
    if(mqtt_client_extensions[i]->init) {
      mqtt_client_extensions[i]->init();
    }
  }
}
/*---------------------------------------------------------------------------*/
PROCESS_THREAD(mqtt_client_process, ev, data)
{
  PROCESS_BEGIN();

  load_manifest_from_savefile();
  sha256_init(&ctx_image);

  // Start verification 
  if(start_verify == 1) {
    if(passed_outer != 1 && passed_inner != 1) {
      check_inner_signature();     
      check_outer_signature();
    }
    if(passed_outer == 1 && passed_inner == 1) {
      // UPDATE HERE 
      puts("[!] Passed both Verifications!");
      char buf[32] = {0};
      int fd = -1;
      fd = cfs_open(MANIFEST_SAVEFILE, CFS_READ | CFS_WRITE);
      if(fd >= 0) {
        cfs_seek(fd, SAVE_OFFSET_SEND_SUCCESS, CFS_SEEK_SET);
        cfs_write(fd, "1", 2);
        cfs_seek(fd, SAVE_OFFSET_SEND_SUCCESS, CFS_SEEK_SET);
        cfs_read(fd, buf, sizeof(buf));
        printf("Written size: %s\n", buf);
        cfs_close(fd);
      }
      send_update_success = 1;

    }
  }
  

  if(init_config() != 1) {
    PROCESS_EXIT();
  }

  init_extensions();

  update_config();

  def_rt_rssi = 0x8000000;
  uip_icmp6_echo_reply_callback_add(&echo_reply_notification,
                                    echo_reply_handler);
  etimer_set(&echo_request_timer, conf.def_rt_ping_interval);

  /* Main loop */
  while(1) {

    PROCESS_YIELD();

    if(ev == button_hal_release_event &&
       ((button_hal_button_t *)data)->unique_id == BUTTON_HAL_ID_BUTTON_ZERO) {
      if(state == STATE_ERROR) {
        connect_attempt = 1;
        state = STATE_REGISTERED;
      }
    }

    if((ev == PROCESS_EVENT_TIMER && data == &publish_periodic_timer) ||
       ev == PROCESS_EVENT_POLL ||
       (ev == button_hal_release_event &&
        ((button_hal_button_t *)data)->unique_id == BUTTON_HAL_ID_BUTTON_ZERO)) {
      state_machine();
    }


    if(ev == PROCESS_EVENT_TIMER && data == &echo_request_timer) {
      ping_parent();
      etimer_set(&echo_request_timer, conf.def_rt_ping_interval);
    }
  }

  PROCESS_END();
}
/*---------------------------------------------------------------------------*/
