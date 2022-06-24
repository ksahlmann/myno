This readme is an extension of the original readme for the whole repository. For information on the installation and running of ESP-32 Boards, the needed devices and the first extension of the netconfclient (excluding events and automations), see Readme.md in main directory.

# General Information
This readme covers the project extension with events and automations being added. For this, the board code had to be substantially expanded. Also the netconfclient was expanded. SSN ontologies are no longer used. A new sensor, bme280, is used to measure temperature, humidity and air pressure. Analog sensors for detecting rain and soil moisture have been added as well.
# The Board

### Sketches
Three sketches are available. `Prec_Agr_Prototype_SensWOUnit` is up to date and stands for Precision Agriculture Prototype Sensorvalues without Units. The sketch `Prec_Agr_Prototype_SensWUnit` is an older version where measurement units are sent with the measurement value. Events are not yet available. The third one: `Prec_Agr_Prototype_SensWOUnit_Sleep` was used for measurements regarding power bank life time. It does not include events or automations.

### RTC Memory
Can be used to save information during deep sleep. So far we save the number of boots and structures containing information on events/automations. When a struct is declared in RTC memory (as it is in the Arduino sketch), all character arrays it contains have to be initialized (like char test[3] = ""), otherwise it will not work (nothing is saved during deep sleep) and there is no error message.

### New Actuators
##### RGB LED
The RGB-Led is similar to the one before. It works with the same code as the last.

##### Pumps
The pumps work well with 4.5 V. The battery boxes I bought need 3 AA batteries and have an on/off switch as well (in the Breadboard_Wiring image i did not find a battery pack with 3 batteries). After each loop the board checks whether the pump is on and turns it off.

The pumps can only pump up to ~45cm high. The time needed to pump 1L of water is around 1.5 minutes at the maximum height and around 40 seconds when the bottom of the container where the water is pumped into is at the same level as the pump. Note: The pump hose can jump around if its not fastened. For emergency stop, use the switch on battery box or twist hose.

I also had a look at the different tutorials supplied. The manual from the manufacturer of the pumps isn't really helpful. The article from Klemens has interesting ideas for assuring that no water damage occurs. However, both articles did not help with how to power the pumps.

### New sensors:
Three sensors have been added.
##### BME280:
A digital sensor that measures humidity, temperature. Almost like the DHT22 from the original project. Parameters from running were taking from the `advancedsettings`-sketch that came with the library. Weather monitoring parameters were used. Forced mode is used to supply energy only when needed (avoids slow heat up of sensor if run permanently as well.)
With this sensor, not two sensors use I2C. This works for now as the light sensor uses address 0x23 and the bme280 uses 0x76.

In soldering, I soldered one bme280 upside down: This is visible since the actual sensor (the grey rectangle is now on the same side as the pins.) Please be careful when wiring it up: VCC and GND!!!, but then it works as intended.

##### Rain Sensor and Moisture Sensor
These are analog sensors. They do not need a library and output a different voltage dependent of their environment. For these two sensors, dry air or dry soil translates to a higher resistance, thus more voltage.
The voltage is then converted by the board into an integer. Note: Arduino boards generally convert into 10 bit integers (0-1023). However, ESP32-Boards use 12-bit integers (0-4095). Do not be confused when reading tutorials for analog sensors using only values from 0 to 1023.

The rain sensor works on 3V and 5V, the moisture sensor when used with 3V does not output 4095 when used outside of soil or in very dry soil. Thus, 5V is needed for the sensor to work correctly.

Also, the sensors have to be calibrated using `Analog_Calib.ino`. Submerging different sensors (even of the same manufacturer) will result in different measurements. A single sensor will also have slightly changing values (generally < 50).

Since calibration is necessary, another Arduino sketch has been written for that. It does repeated measurements and outputs the mean value. Note, the sensor is given time to calibrate for a few seconds. If the measurement starts directly, the sensor outputs 4095 for the first milliseconds regardless of its environment. The calibrated values can then be input into the Precision-Agriculture-sketch at the top. I calibrated the sensors by submerging them up to an imprint of numbers on the back of the sensor. The electronics at the top should not touch water.

The moisture sensors are also capacitance senors. As such, the electronics do not touch the surrounding directly. They are safe to stay in the soil for a longer time without corrosion.

A moisture sensor from the pump set bought first has started to output weird measurement values. It has been clearly marked.

### Breadboard Setup
One board layouts i available. Setup of the boards (electrical) is shown in a `Breadboard_Wiring.png` file within this directory.

Analog sensors have to be around pin 30, since these are analog input pins.
### Libraries
 At the top of the sketches required packages are listed. These can easily be added by selecting "Sketch/Manage libraries" within your sketch *("Sketch/Bibliothek einbinden/Bibliotheken verwalten" in German)* and engaging with the pop-up menu. If not found there, one can add ZIP-libraries via "Sketch/Include library/add .ZIP library" *("Sketch/Bibliothek einbinden/.ZIP Bibliothek hinzufügen")*. The libraries included in the project are given in the table below alongside a link or reference:

| Library| Identifier/LINK | Comment |
|--|--|--|
| Adafruit_BME280.h  | https://github.com/adafruit/Adafruit_BME280_Library | BME280 sensor |

Library may be found using the library manager using library names as search terms. In case of
dependencies ArduinoIDE
will notify you about the dependencies.

If ArduinoIDE is run as a regular user, libraries will be saved in `~/Arduino/libraries`.
Ususally libraries are supplied with a variety of example sketches to try out functionalities of sensors/actuators or else. These are accessible through "File/Examples/" *("Datei/Beispiele")*.

#### Changes to existing libraries:
In the PubSubClient
library the maximum packet size has to be increased: Open PubSubClient.h and change `#define MQTT_MAX_PACKET_SIZE 128` to something like `#define MQTT_MAX_PACKET_SIZE 64000`- After changes to a library, the IDE has to be restarted!

### Common Errors:
Common errors during uploading of sketches in my Ubuntu environment include:
- Package Error (miscalculation of checksum) -> restart upload
- Missing Package Header: -> restart upload
- Serial exception: Could not open port -> unplug and plug in board again. It can help to press the „Boot- Button“ on the board during the upload auf dem Modul, see Documentation to the board.
- My soldering was not that good in the beginning. I had to resolder some of the light sensors by now. In case they show weird measurements, inspect it using the two sketches: `BH1750test_ESP32.ino` to check a sensor that should work correctly and `I2C-Scanner` to check whether I2C works as intended (if no address of changing addresses or the wrong address is found this points to problems with the soldering.)

## Ontologies

#### Versions
Are saved in ontology directory. Includes a long and an optimized version. The current version in long format does only work if split into parts. However the MQTT-bridge cannot handle split up ontologies in case of CRUD-Update.

#### Long Version Error
The reason why the board does not work with the longer version is not known. The MQTT_MAX_PACKET_SIZE has been updated accordingly. At each start up the board also outputs information on the heap. It's big enough to hold the full ontology. The function to send the ontology returns as normal, but the MQTT-broker gets no message.
Also, when output simply to the serial monitor, the full ontology works as well.

#### Older sketches
Older versions of the ontology are available as well. However they do not include events and or automations. In `prototype_units_sent.owl` the units will be sent by the Board and are not included in the ontology. In `prototype_units_notsent.owl` units will not be sent by the Board and are included in the ontology. However, in this early version, information on how to display the unit was hardcoded in the netconf-client. By now, even the unit symbol is part of the ontology, thus these ontologies are out of date.
#### Measurement Units
The ontology has also been updated to include information on measurement units. Thus, the board only sends the measurement values and the client adds units in the GUI.


## Energy Consumption:
The use of powerbanks for powering ESP-32 Boards has been investigated. While it is possible, long time usage needs a higher battery capacity.

General problems:
- The board uses a lot of energy in wifi mode: Spikes of more than 800mA for a few milliseconds have been reported. A first battery-powered powerbank which supplies 500mA was not enough to power the board, when a sketch using wifi, was running.
- exact numbers for energy consumption are not known. Different tutorials provide different numbers (see links below):
https://www.radioshuttle.de/media/tech-infos/esp32-mit-batteriebetrieb/
https://lastminuteengineers.com/esp32-deep-sleep-wakeup-sources/
https://www.elektronikpraxis.vogel.de/ultra-low-power-management-des-esp32-fuer-wifi-iot-module-nutzen-a-738971/

- Using a powerbank, if not enough current is drawn (i.e. in deep sleep) the powerbank shuts off (must do so if sold in the EU), to prevent accidents. Thus, a higher current draw is needed roughly every 30s (in the black/blue powerbanks).

- I also bought a lithium rechargeable battery and a USB-converter. This battery does not shut off if not enough current is drawn

- Analog sensors will draw current, even if the board is in deep sleep (see green LED of rain sensor) and values higher than 5 mA for the moisture sensor have been reported.
- It's hard to translate a powerbanks energy amount into exact runtime (i.e. if the powerbank has 1000mAh and the board uses 10mA, then it can run for 100 hours):
  - The battery inside the powerbank operates at 3.7 V (Lithium battery). For USB the current is converted to 5V (some unknown loss occurs). However in case the USB-connection is used to power the board, the reported values of energy consumption in the links above seem unrealistic.
  - The micro-USB port is connected to a converter again, that converts 5V to 3.3V for the internal circuits on the board (again, some unknown/unspecified loss)
  - Current draw in sending/receiving Wifi-packets has high spikes up to more than 800mA


- The boards could also be powered using the 3.3V pin or 5V pin, but that requires more knowledge in electronics. The 3.3V input needs to be regulated strictly. Different tutorials specifically highlighted the fact that powering using the pins comes at the risk of damaging  the board.

- Even the USB cable used can have significant effects:
https://arduino-hannover.de/2018/07/25/die-tuecken-der-esp32-stromversorgung/

#### Measurements
Multiple measurements (using black/blue powerbanks) were done, showing the difficulties of assessing energy Consumption
- (1) No sleep, every second all sensor values published once: 18.7 hours
- (2) No sleep: every 25 seconds all sensor values once: 20.3 h
- (3) 25 seconds sleep, all sensor values published once: 30.5 h
- (4) 1 hour of sleep, all sensor value published once (using 3000mAh green battery ): ~76 h
##### Conclusions:
- Energy consumption seems largely independent of number of messages sent. Between (1) and (2) only a fraction of the amount of messages is sent, but the runtime is not much longer.
- Even if much of the time is spent in sleep (25 of 30 seconds), we still end of only 12 hours more (about 67% more). Here, the current that the analog sensors draw at all times might be important and could make up much of the energy used: The ESP32 reported uses much less than 1mA in deep sleep (while the moisture sensor might need 5mA and more)

### Events/Automations
Any event or automation is represented by a `struct` per sensor on the board. It is associated with a sensor (only moisture (event and automation) and temperature (event) sensors so far). The board has allocated space for 5 events so far. This number is adjustable, however limited by the space of the RTC-Memory (8kb.). All events/automations are kept in a single array of structs. Each event/automation consists of:
- `ename`: a character representing the name of the event. This has to be unique. If a new event with the same name is created by the user using the netconf-client, the old event will be overwritten without warning
- `eoperator`: a char array: an operator to compare event threshold and measurement value
- `ethreshold`: a float, the threshold at which the event will be triggered
- `einterval`: int: the seconds that pass between two notifications of an event
- `eduration`: int: the duration of the event in seconds. If these pass, the event is reset and notifications stop. This represents an exit point for the board, where it may go to sleep. If the execution continues and the environment has not changed, the same event will be triggered again.
- `elastnotification`: unsigned long: number of milliseconds since last notification. Only used by the board, hidden from user.
- `estart`: unsigned long: miliseconds since event has been triggered. Only used by board, hidden from user.
- `etriggered`: bool: event state, triggered or not: only used by board, hidden from user.
- `eset`: bool: simple state to check, whether the given element of the array is occupied by an event set by the user. This is used to determine whether new events can be set.
- `automoperation`: a char array: This holds a board actutator function that will be executed if the event is triggered. The selection of possible operations is done in the netconf-client. Generally, every actuator function is possible so far.

Events and Automations are mutable by CRUD-Operations. The board checks for free space in case of create and notifies the user if no space is available. If an event already exists it will be updated automatically and vice versa. The read operation returns the discussed elements of an event/automation upon success in the return message/code to the client.

Events are also associated with a new sensor topic. Here, notification messages are sent to. The sensor field changes colors and display the notification message live. See netconf-client section for more details.

### MQTT Problems
##### First Message Delay
I noticed that the boards need more than 10 seconds to receive the response on the first mqtt-message to the broker/bridge. After hours I found out by chance that using delay(x) when waiting for a response can cause problems. I used delay(1000) waiting a second between checking for messages. I do not know why this happened, but when I erased the delay statement, the 10 second gap disappeared.

##### QoS and Sleep
In cases where the board is sent to sleep, sometimes messages were lost, i.e. sensor values not reaching the broker/bridge. Looking at the github and the PubSubClient-Documentation I found out that publish returns the number of bytes it passes to the underlying OSI-structure, but does not flush the buffer or assure that the data was really sent of. The only known work around so far is to wait a certain amount of time before going to sleep after sending data. I found that delay(500) (half a second) seems to work well so far.
In trying to navigate around the problem I also found out that QoS-levels other than zero are not available for publishing but only for subscribing


### Misc
- Die innere Uhr (Quarzkristall) hat Abweichungen von mehr als 5 Prozent, d.h. wenn das Board eine Stunde schlafen soll können Abweichungen von mehr als 3 Minuten auftreten.
- The arduino sketch includes a function to set sensor measurement intervals. It is not yet included in framework and therefore commented out.

- If the board goes into deep sleep, it can be woken up by pressing the RST button.

## Netconf-Client

The Netconf-Client by Nowak has been extended to handle user input for actuators with a form.  For running this Netconf-Client see its Readme file within the directory (no changes from Nowak version).

#### UI Elements for new functionalities
The UI elements are still a little dependent on the name of the function. Older functionalities, like the RGB-LED are identified by the unique `union`-information from the ontolgy. The UI elements for automations are derived by the substring "Auto" in the function name and the elements for configurations by "Conf".

For input parameters that do not have specified min-max values, some boundaries are hard-coded as of now. For example, the event name cannot be more than 15 characters (the lenght of the event name character array on the board) and intervals/durations must be between 1 and 1000 seconds.

For the new event sensor fields new css styles have been introduced. Also the live-change of colors is done in javascript. I am truly no expert on this, but it seems to work well for now. The colors can be changed in the css files.

The event notifications are shown at the top now next to the "Get Devices" button. I did this because I noticed that when many boards are used, after clicking a button my firefox jumps to the top (I do not know why this happens.)

The response codes for READ-operations on events and automations now include not only OK or ERROR, but in case of success also the relevant information on the event.

#### Common Problems
- Drop-Down Menus shutting: Sometimes, the drop-down menus close when you select an option. However, just open it again, the values are saved and the input can then be submitted
