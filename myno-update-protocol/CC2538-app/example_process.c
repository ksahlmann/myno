 #include "contiki.h"
 
 PROCESS(example_process, "Example process");
 AUTOSTART_PROCESSES(&example_process);
 
 PROCESS_THREAD(example_process, ev, data)
 {
   PROCESS_BEGIN();
 
   while(1) {
     PROCESS_WAIT_EVENT();
     printf("Got event number %d\n", ev);
   }
 
   PROCESS_END();
 }