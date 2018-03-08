CONTIKI_PROJECT = energy
CONTIKI_SOURCEFILES += energy.c

CFLAGS += -DPROJECT_CONF_H=\"project-conf.h\"

all: $(CONTIKI_PROJECT)

CONTIKI = ../contiki/iot-lab/parts/contiki/
include $(CONTIKI)/Makefile.include
