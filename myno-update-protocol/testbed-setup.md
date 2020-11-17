# Improving the Performance of the MYNO Update Protocol for IoT Devices
## Testbed setup

The measurements were made in a virtual machine provided by Contiki-NG
(<https://github.com/contiki-ng/contiki-ng/wiki/Vagrant>).
Note: The MQTT broker Mosquitto must be updated to a version >=1.6.0 if that
is not already done. Earlier versions of Mosquitto do not support MQTT v5.

1.  Set up the TI boards as serial devices as described in
    <https://github.com/contiki-ng/contiki-ng/wiki/Platform-cc2538dk#drivers>.

    ``` {basicstyle="\small\ttfamily"}
    sudo modprobe ftdi_sio vendor=0x403 product=0xa6d1
    echo 0403 a6d1 | sudo tee -a /sys/bus/usb-serial/drivers/ftdi_sio/new_id
    ```

2.  If the TI boards are already running the correct programs, skip this step.
    If they are not, run the following commands to compile and upload the programs:
	
    ``` {basicstyle="\small\ttfamily"}
    sudo make PORT=/dev/ttyUSB1 TARGET=cc2538dk mqtt-client.upload
    sudo make PORT=/dev/ttyUSB3 TARGET=cc2538dk border-router.upload
    ```

    The serial port names (`PORT=`) may vary.
	
    The program `border-router.c` may be obtained at <https://github.com/contiki-ng/contiki-ng/tree/release/v4.5/examples/rpl-border-router>.

3.  Start the `tunslip6` tool (included in the Contiki-NG repository in
    the folder `tools`) as described in
    <https://github.com/contiki-ng/contiki-ng/wiki/Tutorial:-RPL-border-router>.

    ``` {basicstyle="\small\ttfamily"}
    sudo contiki-ng/tools/serial-io/tunslip6 -s /dev/ttyUSB3 fd00::1/64
    ```

    The serial port name (`-s`) may vary.

4.  Start the Update Server/NETCONF client and the NETCONF-MQTT bridge.

    ``` {basicstyle="\small\ttfamily"}
    cd MYNO_Update/Prototyp/NETCONF-Bridge
    python3 netconf_server.py
    cd MYNO_Update/Prototyp/NETCONF-Client
    python3 __init__.py
    ```

5.  To monitor the IoT device's logging, run the command:

    ``` {basicstyle="\small\ttfamily"}
    sudo make PORT=/dev/ttyUSB1 TARGET=cc2538dk login
    ```

    The serial port name (`PORT=`) may vary.

    Once it has established connection to the router and the MQTT
    broker, it automatically publishes its device description.

6.  To sniff the IEEE 802.15.4 traffic, plug the TI CC2531 dongle into a
    USB port and run `whsniff`:

    ``` {basicstyle="\small\ttfamily"}
    whsniff -c 26 > trace.pcap
    ```

    The wireless channel (`-c`) may vary. To find out which channel is
    used by the device, see its log output. The resulting trace file can
    be opened with Wireshark.

7.  When the ontology is fully published, the update process can be
    started using the scripts which automatically send the appropriate
    `POST` requests to the web server using valid example data.

    ``` {basicstyle="\small\ttfamily"}
    cd MYNO_Update/Prototyp/tools/example
    ./02-publishUpdateManifestViaWebUI.sh
    ./03-sendImage.sh
    ```

    Alternatively, the web interface (<http://127.0.0.1:5000>) can be
    used.
    To access the web interface from the host system when running the update
    server inside the Vagrant VM, add the following line to the `Vagrantfile`
    in `contiki-ng/tools/vagrant`:

    ``` {basicstyle="\small\ttfamily"}
    config.vm.network "forwarded_port", guest: 5000, host: 5000
    ````

8.  To analyse the `pcap` trace created by `whsniff` using the custom Python
    program `pcap_analysis`, switch to the `pcap_analysis` folder and run
    the command:

    ``` {basicstyle="\small\ttfamily"}
    ./pcap_analysis.py --pcap trace-mup.pcap
    ````

    For more advanced options, see the `README.txt` provided in the folder
    `pcap_analysis`.


Authors: Vera Clemens (2020)
