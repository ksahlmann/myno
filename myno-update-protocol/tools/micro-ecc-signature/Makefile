

all: createSignature.c
	gcc -o createSig uECC.c createSignature.c -lssl -lcrypto

lib: inbuildLibCreateSignature.c
	gcc -o createSigLib uECC.c sha256.c inbuildLibCreateSignature.c