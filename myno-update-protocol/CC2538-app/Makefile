CONTIKI_PROJECT = mqtt-client
all: $(CONTIKI_PROJECT)


CONTIKI = ../../../../../contiki-ng

include $(CONTIKI)/Makefile.dir-variables
MODULES += $(CONTIKI_NG_APP_LAYER_DIR)/mqtt

-include $(CONTIKI)/Makefile.identify-target

MODULES_REL += arch/platform/$(TARGET)
PROJECT_SOURCEFILES += uECC.c 

PROJECT_SOURCEFILES += lzss.c

PLATFORMS_ONLY = cc26x0-cc13x0 cc2538dk openmote zoul native simplelink

include $(CONTIKI)/Makefile.include
