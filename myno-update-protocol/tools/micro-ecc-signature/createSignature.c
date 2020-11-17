//
// Created by MNowak1412@gmail.com on 11.01.20.
//

#include "uECC.h"

#include <stdlib.h>
#include <stdio.h>
#include <openssl/sha.h>
#include <stddef.h>
#include <errno.h>
#include <string.h>
#include <ctype.h>
#include <assert.h>

#define DEBUG
//#define DEBUGSIGN

uint8_t privateManufacturer[32] = {0x90, 0x1a, 0x2e, 0x11, 0xe1, 0xb6, 0x54, 0xfe, 0x15, 0xf, 0x4d, 0x76, 0x82, 0x66,
                                   0x73, 0xe1, 0x21, 0x6c, 0x57, 0x9a, 0x3c, 0x46, 0xa8, 0x76, 0x37, 0xc7, 0x6e, 0x7a,
                                   0x63, 0x67, 0xed, 0x5d};
uint8_t publicManufacturer[64] = {0x6e, 0x1f, 0x4e, 0x97, 0x5c, 0xbb, 0x89, 0xa4, 0x9, 0x1d, 0xb5, 0xb8, 0x8e, 0x7e,
                                  0x81, 0xbf, 0x8, 0x99, 0x77, 0x68, 0x4e, 0x88, 0xb3, 0x93, 0xda, 0x7, 0x37, 0x95,
                                  0x9a, 0xbf, 0x48, 0x32, 0x76, 0x6e, 0xdb, 0x4a, 0x35, 0xdf, 0x53, 0x89, 0x3a, 0xd1,
                                  0xf2, 0xbe, 0xd0, 0x1d, 0xe, 0x2a, 0xc6, 0x92, 0xc1, 0x30, 0x5a, 0x22, 0xba, 0x24,
                                  0x99, 0xe4, 0x41, 0x2, 0x1c, 0x12, 0x52, 0xf0};


uint8_t privateUpdateserver[32] = {0x1b, 0x7b, 0xab, 0x8d, 0x66, 0xa1, 0x77, 0xa9, 0xce, 0x60, 0x74, 0xa, 0x1f, 0xec,
                                   0xbf, 0x69, 0xf7, 0xa8, 0x70, 0x1b, 0x50, 0x11, 0x6f, 0x2d, 0xd, 0x25, 0xff, 0x82,
                                   0xf6, 0xd0, 0x63, 0xb0};

uint8_t publicUpdateserver[64] = {0xbc, 0x4d, 0xca, 0xf0, 0x77, 0xc2, 0xc8, 0x60, 0x43, 0x1f, 0x73, 0x8f, 0xce, 0xa8,
                                  0x8e, 0xea, 0xdf, 0xe1, 0xda, 0x5f, 0x1d, 0x18, 0x3e, 0x38, 0x2d, 0x38, 0x14, 0x69,
                                  0xa5, 0x77, 0x0, 0x67, 0x4c, 0x2d, 0xf3, 0x41, 0xa4, 0x80, 0x5b, 0x59, 0x17, 0x5b,
                                  0x16, 0x69, 0x9e, 0xdd, 0x66, 0xb4, 0x49, 0x64, 0xaf, 0xc7, 0x41, 0x52, 0x6, 0xb,
                                  0xfe, 0x9d, 0xd7, 0x9e, 0x9, 0xbf, 0xc5, 0xd7};


uint8_t hash[32] = {0xef, 0xf1, 0x0, 0xad, 0x25, 0x31, 0x70, 0x5e, 0xd2, 0x43, 0xd4, 0xcd, 0xcc, 0xf, 0x49, 0x44, 0x24, 0x1f, 0x5d, 0xb7, 0x49, 0xea, 0x59, 0x73, 0x77, 0xf8, 0xac, 0x8f, 0xca, 0x2f, 0x27, 0x46};

uint8_t sig[64] = {
        0xf4, 0x18, 0xc7, 0x5, 0x6e, 0x58, 0x28, 0x33, 0x9c, 0x24, 0xa0, 0xac, 0x87, 0xfb, 0xe7,
        0x43, 0xde, 0xa0, 0x8b, 0x56, 0x87, 0xe6, 0xcb, 0x71, 0x6, 0xd3, 0x5e, 0xad, 0x2c, 0xfb,
        0x4f, 0xe4, 0xd7, 0x44, 0x92, 0xb7, 0xda, 0x77, 0xf5, 0x91, 0x2a, 0xb3, 0x4c, 0xb6, 0x68,
        0x70, 0x86, 0x91, 0x4d, 0xc4, 0x6d, 0xea, 0xd5, 0xf5, 0x9, 0x9e, 0x75, 0x38, 0xe2, 0x4e,
        0x43, 0x34, 0xb3, 0xa1};

uint8_t newsig[64 ]={0};

const struct uECC_Curve_t * curve;

void sha256_hash_string(char hash[SHA256_DIGEST_LENGTH], uint8_t outputBuffer[65])
{
    int i = 0;

    for(i = 0; i < SHA256_DIGEST_LENGTH; i++)
    {
        sprintf(outputBuffer + (i * 2), "%02x", (uint8_t)hash[i]);
    }

    outputBuffer[64] = 0;
}

void sha256(char *string, char outputBuffer[65])
{
    unsigned char hash[SHA256_DIGEST_LENGTH];
    int len;
    SHA256_CTX sha256;
    SHA256_Init(&sha256);

    len=strlen(string);
    SHA256_Update(&sha256, string,len);
    SHA256_Final(hash, &sha256);
    //printf("\nHASH: \n");
    int i = 0;
    for(i = 0; i < SHA256_DIGEST_LENGTH; i++)
    {
    //    printf("0x%02x, ", hash[i]);
        sprintf(outputBuffer + (i * 2), "%02x", (unsigned char)hash[i]);
    }
    outputBuffer[64] = 0;
}

void hexString(unsigned char *bytes, int bytesLength, char *dest)
{
    char lookup[16] = { '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f' };
    for (int i = 0; i < bytesLength; i++) {
        dest[2*i  ] = lookup[(bytes[i]>>4)&0xF];
        dest[2*i+1] = lookup[bytes[i] & 0xF];
    }
    dest[2*bytesLength] = 0;
}

int create_keys(){
    uint8_t private[32] = {};
    uint8_t public[64] = {};
    uint8_t hash[32] = {};
    uint8_t sig[64] = {};


    if (!uECC_make_key(public, private, curve)) {
        printf("\nuECC_make_key() failed\n");
        return 1;
    }

    if (!uECC_sign(private, hash, sizeof(hash), sig, curve)) {
        printf("\nuECC_sign() failed\n");
        return 1;
    }

    if (!uECC_verify(public, hash, sizeof(0), sig, curve)) {
        printf("\nuECC_verify() failed\n");
        return 1;
    }

    puts("[+] private Key is:");
    for(int i = 0; i != 32; i++){
        if(i == 31){
            printf("0x%02x\n", private[i]);
        }else{
            printf("0x%02x, ", private[i]);
        }
    }
    puts("\n[+] public Key is: ");
    for(int i = 0; i != 32; i++){
        if(i == 31){
            printf("0x%02x, ", public[i]);
        }else{
            printf("0x%02x, ", public[i]);
        }
    }
    for(int i = 32; i != 64; i++){
        if(i == 63){
            printf("0x%02x\n", public[i]);
        }else{
            printf("0x%02x, ", public[i]);
        }
    }
}

static uint8_t hashBuffer[65] = "";

int main(int argc, char **argv){

    curve = uECC_secp256r1();
    
    if(argc < 2)
    {
        fprintf(stderr, "usage: ./createSig\n'./createSig gen': Create new Keys\n'./createSig signM String': Sign String with private Key of Manufacturer\n'./createSig signU String': Sign String with private Key of the Update Server\n'./createSig verify': Testcase for validating stored values \n'./createSig verifyHash (Manufacturer or Updateserver) (Hash to verify) (signature to verify)': verify custom values \n");
        return 1;
    }

    if(strcmp(argv[1], "gen") == 0){
        printf("[+] Creating new Keys: \n");
        create_keys();
    } else if(strcmp(argv[1], "signM") == 0){
        sha256(argv[2], hashBuffer);
        for (uint8_t i=0; i<strlen(hashBuffer)/2+1;i++) {
            hash[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = hashBuffer[(i*2)+j];
                if (firstchar >= '0' && firstchar <= '9') {
                    hash[i] = hash[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    hash[i] = hash[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    hash[i] = hash[i]*16 + firstchar - 'a' + 10;
                }
            }
        }
        if (!uECC_sign(privateManufacturer, hash, sizeof(hash), sig, curve)) {
            printf("uECC_sign() failed\n");
            return -1;
        }
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("%02x\n", sig[i]);
            }else{
                printf("%02x", sig[i]);
            }
        }
    }else if(strcmp(argv[1], "signU") == 0){
        sha256(argv[2], hashBuffer);
        for (uint8_t i=0; i<strlen(hashBuffer)/2+1;i++) {
            hash[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = hashBuffer[(i*2)+j];
                if (firstchar >= '0' && firstchar <= '9') {
                    hash[i] = hash[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    hash[i] = hash[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    hash[i] = hash[i]*16 + firstchar - 'a' + 10;
                }
            }
        }
#ifdef DEBUGSIGN
        puts("[+] hash is:");
        for(int i = 0; i != 32; i++) {
            if (i == 31) {
                printf("%02x\n", hash[i]);
            } else {
                printf("%02x", hash[i]);
            }
        }
        puts("[+] Private Key is:");
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("%02x\n", privateUpdateserver[i]);
            }else{
                printf("%02x", privateUpdateserver[i]);
            }
        }
        puts("[+] Signature is:");
#endif
        if (!uECC_sign(privateUpdateserver, hash, sizeof(hash), sig, curve)) {
            printf("uECC_sign() failed\n");
            return -1;
        }
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("%02x\n", sig[i]);
            }else{
                printf("%02x", sig[i]);
            }
        }
    }
    // verify the stored values
    else if(strcmp(argv[1], "verify") == 0){
        if (!uECC_verify(publicUpdateserver, hash, sizeof(hash), sig, curve)) {
            printf("\nuECC_verify() failed\n");
            return 1;
        }
        printf("\nuECC_verify() worked\n");
    }
    // verify custom values
    // 1 Argument: Keyword "verifyHash"
    // 2 Argument: Manufacturer (1) or Updateserver (2)
    // 3 Argument: Hash to verify
    // 4 Argument: signature to verify
    else if(strcmp(argv[1], "verifyHash") == 0){
        uint8_t publicKey[64] = {0};
        char *messagebuffer;

        // Get right key
        if(strcmp(argv[2], "1") == 0 ){
            //puts("setting Manufacturer");
            memcpy( publicKey, publicManufacturer, sizeof(publicManufacturer));
        }else{
            // puts("setting Updateserver");
            memcpy( publicKey, publicUpdateserver, sizeof(publicUpdateserver));
        }

        messagebuffer = argv[3];

        // Load Hash to Variable and convert string
        for (uint8_t i=0; i<strlen(messagebuffer)/2+1;i++) {
            hash[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = messagebuffer[(i*2)+j];
                //printf("outerSignature[%d] = %3d messagebuffer[%d+%d] = %c ", i, outerSignature[i], i, j, messagebuffer[(i*2)+j]);
                if (firstchar >= '0' && firstchar <= '9') {
                    hash[i] = hash[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    hash[i] = hash[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    hash[i] = hash[i]*16 + firstchar - 'a' + 10;
                }
            }
        }



        messagebuffer = argv[4];
        //printf("%s", messagebuffer);

        // Load Signature to Variable and convert string
        for (uint8_t i=0; i<strlen(messagebuffer)/2+1;i++) {
            sig[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = messagebuffer[(i*2)+j];
                //printf("outerSignature[%d] = %3d messagebuffer[%d+%d] = %c ", i, outerSignature[i], i, j, messagebuffer[(i*2)+j]);
                if (firstchar >= '0' && firstchar <= '9') {
                    sig[i] = sig[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    sig[i] = sig[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    sig[i] = sig[i]*16 + firstchar - 'a' + 10;
                }
            }
        }
#ifdef DEBUG
        puts("[+] Public Key is:");
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("%02x\n", publicKey[i]);
            }else{
                printf("%02x", publicKey[i]);
            }
        }
        puts("[+] hash is:");
        for(int i = 0; i != 32; i++){
            if(i == 31){
                printf("%02x\n", hash[i]);
            }else{
                printf("%02x", hash[i]);
            }
        }
        puts("[+] sig is:");
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("%02x\n", sig[i]);
            }else{
                printf("%02x", sig[i]);
            }
        }
#endif

        if (!uECC_verify(publicKey, hash, sizeof(hash), sig, curve)) {
#ifdef DEBUG
            puts("[+] Didnt Work");
#endif
            return 1;
        }
#ifdef DEBUG
        puts("[!] WORKED");
#endif
        return 0;
    }
    //sign all in one go
    else if(strcmp(argv[1], "signAll") == 0){
        sha256(argv[3], hashBuffer);
        char signature[128] = {0};
        char outerSignatureBuffer[512] = {0};
        strcat(outerSignatureBuffer, argv[3]);


        char *device_token = argv[2];
#ifdef DEBUG
        printf("\n[+] String to sign is: %s", argv[3]);
        printf("\n[+] Hash is: %s\n", hashBuffer);
#endif
        for (uint8_t i=0; i<strlen(hashBuffer)/2+1;i++) {
            hash[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = hashBuffer[(i*2)+j];
                if (firstchar >= '0' && firstchar <= '9') {
                    hash[i] = hash[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    hash[i] = hash[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    hash[i] = hash[i]*16 + firstchar - 'a' + 10;
                }
            }
        }

        if (!uECC_sign(privateManufacturer, hash, sizeof(hash), newsig, curve)) {
            printf("uECC_sign() failed\n");
            return -1;
        }
#ifdef DEBUG
        else{
            puts("[+] Signing succeeded");
        }

        puts("[+] Public Key Manufacturer is:");
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("0x%02x\n", publicManufacturer[i]);
            }else{
                printf("0x%02x, ", publicManufacturer[i]);
            }
        }

        puts("[+] Inner Signature is:");
#endif

        for(int i = 0; i != 64; i++){

            if(i == 63){
                printf("%02x\n", newsig[i]);
            }else{
                printf("%02x", newsig[i]);
            }
        }

        //memset(newsig, '0', sizeof(newsig));

        hexString(newsig, 64, signature);

        char buf[1024];
        snprintf(buf, sizeof buf, "%s;%s;%s", argv[3], signature, device_token);

        sha256(buf, hashBuffer);

#ifdef DEBUG
        printf("[+] Gehashed wurde: %s\n",buf);
        printf("[+] Hash is: %s\n", hashBuffer);
#endif
        for (uint8_t i=0; i<strlen(hashBuffer)/2+1;i++) {
            hash[i] = 0;
            for (uint8_t j=0; j<2; j++) {
                char firstchar = hashBuffer[(i*2)+j];
                if (firstchar >= '0' && firstchar <= '9') {
                    hash[i] = hash[i]*16 + firstchar - '0';
                } else if (firstchar >= 'A' && firstchar <= 'F') {
                    hash[i] = hash[i]*16 + firstchar - 'A' + 10;
                } else if (firstchar >= 'a' && firstchar <= 'f') {
                    hash[i] = hash[i]*16 + firstchar - 'a' + 10;
                }
            }
        }

        if (!uECC_sign(privateUpdateserver, hash, sizeof(hash), newsig, curve)) {
            printf("uECC_sign() failed\n");
            return -1;
        }
#ifdef DEBUG
        else{
            puts("[+] Signing succeeded");
        }
        puts("[+] Outer Signature is:");
#endif
        for(int i = 0; i != 64; i++){

            if(i == 63){
                printf("%02x\n", newsig[i]);
            }else{
                printf("%02x", newsig[i]);
            }
        }
        puts("[+] Public Key Updateserver is:");
        for(int i = 0; i != 64; i++){
            if(i == 63){
                printf("0x%02x\n", publicUpdateserver[i]);
            }else{
                printf("0x%02x, ", publicUpdateserver[i]);
            }
        }

    }
    return 0;
}
