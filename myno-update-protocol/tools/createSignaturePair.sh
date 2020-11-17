#!/bin/bash
# Create a pair of signatures
cd micro-ecc-signature

appid="APP"
link_Offset="0"
hash_manifest="17c36f0ade2e54c614c2c5aef5e39cbc24d228c954222bf985026bf4fe18540d"
size="100719"
version="2"
old_version="1"
innerSignature=""
deviceNonceManifest=""
outerSignature=""

device_token="123456"

make 
./createSig signAll $device_token $appid";"$link_Offset";"$hash_manifest";"$size";"$version";"$old_version
