# pythinkgear

Python utility to interface with Thinkgear-based Brain Computer Interface
devices such as the Neurosky Mindset.


## Setup under Linux

Here are the instructions to make the Mindset available as a serial
device suitable for direct access by `pythinkgear` under Ubuntu 11.04:

- As root create a file named `/etc/bluetooth/rfcomm.conf` to define a serial
  binding `/dev/rfcomm0` for the bluetooth device. Configure it as follows
  (replace the device id to match your own):

        rfcomm0 {
            # Automatically bind the device at startup
            bind yes;

            # Bluetooth address of the device found on a tag of the inner
            # headband of the headset
            device 00:13:EF:00:32:04;

            # RFCOMM channel for the connection
            channel 3;

            # Description of the connection
            comment "MindSet";
        }

- Perform bluetooth pairing using the gnome bluetooth-applet:

  - Ensure the headset battery is loaded (use the USB cable if not)
  - Turn it on by holding the power on button for more that 1s, the blue led
    should flash
  - Hold the "Play / Pause" button for a couple of seconds: the blue and red
    leds should now flash.
  - In the bluetooth preferences, click "add new device" and follow the wizard
    using the default settings (no PIN option necessary).
  - Once the headset is paired and connected, the blue led should stay on.

- Bind the bluetooth device as onto the `rfcomm0` virtual serial port:

        sudo rfcomm bind /dev/rfcomm0

- If you get "Can't create device: Address already in use" error message, try to
  unbind and rebind:

        sudo rfcomm unbind /dev/rfcomm0
        sudo rfcomm bind /dev/rfcomm0

- Put the headset on your head and ensure the metal contacts can all touch your
  skin (hear and forehead), then wait a couple of second with the headset in
  place.

- Test the pythinkgear main script, you should get DEBUG level log info on the
  various waves + thinkgear specific measures of ATTENTION and MEDITATION:

        python thinkgear/thinkgear.py /dev/rfcomm0
        INFO:root:Opening connection to /dev/rfcomm0
        DEBUG:__main__:ASIC EEG Power: EEGPowerData(delta=166592, theta=27561, lowalpha=5090, highalpha=9488, lowbeta=3325, highbeta=8027, lowgamma=3522, midgamma=2735)
        DEBUG:__main__:ATTENTION eSense: 40
        DEBUG:__main__:MEDITATION eSense: 50

  Sometimes however the mindset looses the connection and it's impossible
  to reconnect from the gnome applet nor to redo the pairing. Even forcing
  the unload of the bluetooth kernel module does not fixes the issue. A
  system restart is required.

## TODO

Real time computation of the spectrogram, with embedded HTTP server and
simple Ajax png based UI or streaming video for live broadcasting a visual
representation of your mind on the web.

<http://classicalconvert.com/2008/04/how-to-visualize-music-using-animated-spectrograms-with-open-source-everything/>
