# MYNO key distribution and create signature 

You will need two key pairs: Manufacturer and Update-Server/NETCONF-Client. These will own the Private Keys. 
The Device will get the Public Keys of both. 

## 1. Create both key pairs 

The new key pairs can be created with a tool for manufacturer and Update-Server by the following call: 

```bash
# create new key pairs 
./createSig gen
```
The output could be like this: 
```bash
% bash createSignaturePair.sh
gcc -o createSig uECC.c createSignature.c -lssl -lcrypto

[+] String to sign is: APP;0;17c36f0ade2e54c614c2c5aef5e39cbc24d228c954222bf985026bf4fe18540d;100719;2;1
[+] Hash is: 7adb5951cfec2b6374e4bc444fc4baf59e8aab7c39adfdffcd8448098deb5c21
[+] Signing succeeded
[+] Public Key Manufacturer is:
0x6e, 0x1f, 0x4e, 0x97, 0x5c, 0xbb, 0x89, 0xa4, 0x09, 0x1d, 0xb5, 0xb8, 0x8e, 0x7e, 0x81, 0xbf, 0x08, 0x99, 0x77, 0x68, 0x4e, 0x88, 0xb3, 0x93, 0xda, 0x07, 0x37, 0x95, 0x9a, 0xbf, 0x48, 0x32, 0x76, 0x6e, 0xdb, 0x4a, 0x35, 0xdf, 0x53, 0x89, 0x3a, 0xd1, 0xf2, 0xbe, 0xd0, 0x1d, 0x0e, 0x2a, 0xc6, 0x92, 0xc1, 0x30, 0x5a, 0x22, 0xba, 0x24, 0x99, 0xe4, 0x41, 0x02, 0x1c, 0x12, 0x52, 0xf0
[+] Inner Signature is:
ae206610741258076aba2fc31a4ad77e9c1c34e3efb4c79884133d72da5839f1c5c3c37b0bb75586267273c339f56b42f660d268018a2b85290b8096e91f7161
[+] Gehashed wurde: APP;0;17c36f0ade2e54c614c2c5aef5e39cbc24d228c954222bf985026bf4fe18540d;100719;2;1;ae206610741258076aba2fc31a4ad77e9c1c34e3efb4c79884133d72da5839f1c5c3c37b0bb75586267273c339f56b42f660d268018a2b85290b8096e91f7161;123456
[+] Hash is: a793db5e488a422ee3a4ad24f1a9e44c35e3f806af75e0331ff6c1cd7ea50ba4
[+] Signing succeeded
[+] Outer Signature is:
e541d5dfff1cdebf6fc94550269b02643031557bc738288e8b15cd71e1b1170b81772aca1318fba0349161f1007f86950801fdde01f4ecb9d40db79c52f21a99
[+] Public Key Updateserver is:
0xbc, 0x4d, 0xca, 0xf0, 0x77, 0xc2, 0xc8, 0x60, 0x43, 0x1f, 0x73, 0x8f, 0xce, 0xa8, 0x8e, 0xea, 0xdf, 0xe1, 0xda, 0x5f, 0x1d, 0x18, 0x3e, 0x38, 0x2d, 0x38, 0x14, 0x69, 0xa5, 0x77, 0x00, 0x67, 0x4c, 0x2d, 0xf3, 0x41, 0xa4, 0x80, 0x5b, 0x59, 0x17, 0x5b, 0x16, 0x69, 0x9e, 0xdd, 0x66, 0xb4, 0x49, 0x64, 0xaf, 0xc7, 0x41, 0x52, 0x06, 0x0b, 0xfe, 0x9d, 0xd7, 0x9e, 0x09, 0xbf, 0xc5, 0xd7
```

The values can be changed in the Bash-Script:

```bash
# header of file createSignaturePair.sh
appid="APP"
link_Offset="0"
hash_manifest="0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894"
size="555"
version="2"
old_version="1"
innerSignature=""
deviceNonceManifest=""
outerSignature=""

device_token="123456"
```

### 2. Distribute the generated keys 

#### Script
The private key must be placed in the script ```MYNO_Update/Prototyp/tools/micro-ecc-signature/createSignature.c```:
```c
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
```

#### NETCONF-Client

The Script must be ajusted and new compiled: 

```bash
cd myno-update-protocol/tools/micro-ecc-signature/
make 
```

The resulted compilation must placed into NETCONF-Client: 

```
myno-update-protocol/update-server/createSig
```

##### MYNO-Device
The device code must include the public key. The key code is in the file ```myno-update-protocol/CC2538-app/Keys.h``` : 

```c
static uint8_t publicUpdateserver[64] = {0xbc, 0x4d, 0xca, 0xf0, 0x77, 0xc2, 0xc8, 0x60, 0x43, 0x1f, 0x73, 0x8f, 0xce, 
0xa8, 0x8e, 0xea, 0xdf, 0xe1, 0xda, 0x5f, 0x1d, 0x18, 0x3e, 0x38, 0x2d, 0x38, 0x14, 0x69, 0xa5, 0x77, 0x0, 0x67, 
0x4c, 0x2d, 0xf3, 0x41, 0xa4, 0x80, 0x5b, 0x59, 0x17, 0x5b, 0x16, 0x69, 0x9e, 0xdd, 0x66, 0xb4, 0x49, 0x64, 0xaf, 
0xc7, 0x41, 0x52, 0x6, 0xb, 0xfe, 0x9d, 0xd7, 0x9e, 0x9, 0xbf, 0xc5, 0xd7};
static  uint8_t publicManufacturer[64] = {0x6e, 0x1f, 0x4e, 0x97, 0x5c, 0xbb, 0x89, 0xa4, 0x9, 0x1d, 0xb5, 0xb8, <
0x8e, 0x7e, 0x81, 0xbf, 0x8, 0x99, 0x77, 0x68, 0x4e, 0x88, 0xb3, 0x93, 0xda, 0x7, 0x37, 0x95, 0x9a, 0xbf, 0x48, 
0x32, 0x76, 0x6e, 0xdb, 0x4a, 0x35, 0xdf, 0x53, 0x89, 0x3a, 0xd1, 0xf2, 0xbe, 0xd0, 0x1d, 0xe, 0x2a, 0xc6, 0x92, 
0xc1, 0x30, 0x5a, 0x22, 0xba, 0x24, 0x99, 0xe4, 0x41, 0x2, 0x1c, 0x12, 0x52, 0xf0};
```

## 3. Build the Device with keys 

Execute make command for the MYNO-Device. 
Upload this application on a device. 

## 4. Create new version of the Firmware Update Image 

Change something in code, e.g. new version in the header. 
Execute make command.

## 5. Compress the Firmware Update Image with lzss

Execute the Python Script with arguments input and output. The file of the Update-Firmware ```mqtt-client.cc2538dk``` will be compressed. Skript is in folder: ```myno-update-protocol\tools\compress_image.py```.

Example: 
```bash
# Input: mqtt-client.cc2538dk
# Output: mqtt-client.compressed 
./compress_image.py mqtt-client.cc2538dk mqtt-client.compressed
# output:
mqtt-client.cc2538dk
```


## 6. Create Hash from the Firmware Update Image 

The SHA256 Hash will be created from the compressed Firmware Update Image.

Under Linux use the command sha256sum, where the FILE the Firmware Update Image file is:

```bash
cd folder/der/
sha256sum FILE
```


## 7. Create inner and outer Signatures

If the steps from the point 2 cannot be used, the signatures can be generated separately. The Hash value from the Update-Manifest can be signed as following: 

```bash
# Create inner Signature
./createSig signM "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1"
# create outer siganture from string
./createSig signU "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1;a17e9cdfb8efbf590adde3e805adcbc6946900f1da61b17ade7164969072d43ce7aaecfa092471ca1c339d08b00edc79a1384511470e5382a3231a33a33130db;123456"
```
