# createSignatures

Hilfsprogramm um Signaturen für den MYNO Update Prozess zu erstellen. Nähere Angaben zur Nutzung in der übergeordneten Readme gelesen werden.  

### Genutzte Projekte: 

```
https://github.com/kmackay/micro-ecc
https://github.com/B-Con/crypto-algorithms/blob/master/sha256.c
https://github.com/B-Con/crypto-algorithms/blob/master/sha256.c
```

Die Implementierung von micro-ecc wird mit folgenden Dateien genutzt:  

```
micro-ecc-signature
├── curve-specific.inc
├── library.properties
├── LICENSE.txt
├── Makefile
├── platform-specific.inc
├── Readme.md
├── types.h
├── uECC.c
├── uECC.h
└── uECC_vli.h
```

Die beiden sha256.(c|h) sind die Implementierung für den Hashing Algorithmus aus den oben genannten zwei letzten Quellen. 

```
micro-ecc-signature
├── sha256.c
└── sha256.h
```

Die Implementierung der Funktionalitäten finden sich in den folgenden Dateien: 

```
micro-ecc-signature
├── createSignature.c
├── Makefile
├── inbuildLibCreateSignature.c
└── createSig
```

Das Makefile besitzt zwei Targets, all mit einer getesteten Version die jedoch die openssl development headers voraussetzt und 'lib' welches die sha256 libary von oben nutzt. 

Aus Ubuntu 18.04 installieren sich die OpenSSL Header mit den folgenen Befehlen: 
```bash
sudo apt update 
sudo apt install -y libssl-dev 
```


## Beispielnutzung

Ein String kann direkt signiert werden mit:  

```bash
# Erstelle eine innere Signatur
./createSig signM "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1"
# create a a outer siganture from string
./createSig signU "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1;a17e9cdfb8efbf590adde3e805adcbc6946900f1da61b17ade7164969072d43ce7aaecfa092471ca1c339d08b00edc79a1384511470e5382a3231a33a33130db;123456"
```

Der Output wäre hierbei die jeweilige Signatur:

```bash
./createSig signU "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1"
15d58afcfe424a2de791c0b17682a366a0dc5885342dfc088d7ab2deeb40957cdc5b227f711fdf47fb1414ccb794f4a3cc56f7721c67e1ff49bee2f9fc

./createSig signU "APP;0;0b7a2d44cd0dc6f00a7f17b383747c89c24a1d21f77652dbee61feb62ca65894;555;2;1;a17e9cdfb8efbf590adde3e805adcbc6946900f1da61b17ade7164969072d43ce7aaecfa092471ca1c339d08b00edc79a1384511470e5382a3231a33a33130db;123456"
83e3a111621bbeb113fe979c9948da31d588fa4cc411fe7372fd06b6834637718e3bae6601d2c668788bb8f81c6ada797a5abea44e0fe96efa239725ee15c31
```

##### Erstellung von neuen Schlüsseln 
Mit dem Progeamm können neue Schlüssel für den Hersteller und Updateserver erstellt werden. Diese werden mit dem folgenden Aufruf erstellt: 
```bash
# Erstelle neue Schlüsselpaare 
./createSig gen
```
Eine Ausgabe könnte so aussehen: 
```bash
./createSig gen
[+] Creating new Keys: 
[+] private Key is:
0xe3, 0x2d, 0x14, 0xc6, 0x93, 0x3c, 0xa2, 0x74, 0xf5, 0xb6, 0x47, 0x68, 0xcf, 0xd8, 0x42, 0x5b, 0x4e, 0x4d, 0xb6, 0xe5, 0xbf, 0x46, 0xf5, 0x2a, 0xb2, 0x6e, 0x46, 0x15, 0x5e, 0x03, 0x5c, 0xc4

[+] public Key is: 
0x02, 0x94, 0x4a, 0x38, 0x4b, 0x5f, 0x51, 0x95, 0x0e, 0xe7, 0x17, 0xcc, 0x0c, 0xa2, 0xea, 0xa8, 0x4b, 0x51, 0x51, 0xe1, 0x4e, 0x91, 0x04, 0x25, 0x01, 0xde, 0xc9, 0xb3, 0x23, 0x35, 0x71, 0xb4, 0x49, 0xab, 0x6c, 0x62, 0x4e, 0x49, 0xf5, 0x14, 0xfd, 0x1d, 0x3a, 0x00, 0xa0, 0x29, 0x69, 0x16, 0xca, 0xcd, 0x6f, 0x2e, 0x5f, 0xa4, 0xad, 0xd9, 0x73, 0xb9, 0x1b, 0x1e, 0xca, 0x30, 0x33, 0xfc
```

Die Schlüssel können dann in die entsprechenden Programme eingepflegt werden. Diese wären: 

#### NETCONF-Client
Das Dienstprogramm für den Updateserver und den Hersteller: 
```
MYNO_Update/Prototyp/tools/micro-ecc-signature/createSignature.c
```
Dieses muss neu erstellt und das resultierende Programm im NETCONF-Client entsprechend abgelegt werden, unter: 
```
MYNO_Update/Prototyp/NETCONF-Client/createSig
```
##### MYNO-Device
Hier muss das neue öffentliche Schlüsselmaterial eingepflegt und im Anschluss auf das Gerät geladen werden. Die entsprechenden Stellen im Quellcode sind in der Datei ```MYNO_Update/Prototyp/MYNO-Device/Keys.h``` : 

```c
static uint8_t publicUpdateserver[64] = {0xbc, 0x4d, 0xca, 0xf0, 0x77, 0xc2, 0xc8, 0x60, 0x43, 0x1f, 0x73, 0x8f, 0xce, 
0xa8, 0x8e, 0xea, 0xdf, 0xe1, 0xda, 0x5f, 0x1d, 0x18, 0x3e, 0x38, 0x2d, 0x38, 0x14, 0x69, 0xa5, 0x77, 0x0, 0x67, 
0x4c, 0x2d, 0xf3, 0x41, 0xa4, 0x80, 0x5b, 0x59, 0x17, 0x5b, 0x16, 0x69, 0x9e, 0xdd, 0x66, 0xb4, 0x49, 0x64, 0xaf, 
0xc7, 0x41, 0x52, 0x6, 0xb, 0xfe, 0x9d, 0xd7, 0x9e, 0x9, 0xbf, 0xc5, 0xd7};
static  uint8_t publicManufacturer[64] = {0x6e, 0x1f, 0x4e, 0x97, 0x5c, 0xbb, 0x89, 0xa4, 0x9, 0x1d, 0xb5, 0xb8, 
0x8e, 0x7e, 0x81, 0xbf, 0x8, 0x99, 0x77, 0x68, 0x4e, 0x88, 0xb3, 0x93, 0xda, 0x7, 0x37, 0x95, 0x9a, 0xbf, 0x48, 
0x32, 0x76, 0x6e, 0xdb, 0x4a, 0x35, 0xdf, 0x53, 0x89, 0x3a, 0xd1, 0xf2, 0xbe, 0xd0, 0x1d, 0xe, 0x2a, 0xc6, 0x92, 
0xc1, 0x30, 0x5a, 0x22, 0xba, 0x24, 0x99, 0xe4, 0x41, 0x2, 0x1c, 0x12, 0x52, 0xf0};
```
