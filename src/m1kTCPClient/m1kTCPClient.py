"""TCP client to TCP server for SMU."""

import ast
import socket


class m1kTCPClient:
    """TCP client to TCP server for SMU."""

    def __init__(self, HOST, PORT, TERMCHAR="\n", timeout=30, plf=50):
        """Construct TCP client for SMU.

        Parameters
        ----------
        HOST : str
            IPv4 address or hostname of server.
        PORT : int
            Server port.
        TERMCHAR : str
            Message termination character string.
        plf : float or int
            Power line frequency (Hz).
        ch_per_board : {1, 2}
            Number of channels to use per ADALM1000 board. If 1, channel A is assumed
            as the channel to use. This cannot be changed once the object has been
            instantiated.
        """
        self.HOST = HOST
        self.PORT = PORT
        self._TERMCHAR = TERMCHAR
        self._TERMCHAR_BYTES = TERMCHAR.encode()
        self.timeout = timeout

        self._query(f"plf {plf}")

    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the runtime context related to this object.

        Make sure everything gets cleaned up properly.
        """
        pass

    @property
    def TERMCHAR(self):
        """Get termination character."""
        return self._TERMCHAR

    @TERMCHAR.setter
    def TERMCHAR(self, TERMCHAR):
        """Set termination character."""
        self._TERMCHAR = TERMCHAR
        self._TERMCHAR_BYTES = TERMCHAR.encode()

    @property
    def TERMCHAR_BYTES(self):
        """Get termination character as byte string."""
        return self._TERMCHAR_BYTES

    def _query(self, msg):
        """Query the SMU.

        Parameters
        ----------
        msg : str
            Query message.

        Returns
        -------
        resp : str
            Instrument response.
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.timeout)

            s.connect((self.HOST, self.PORT))

            s.sendall(msg.encode() + self.TERMCHAR_BYTES)

            buf = b""
            while True:
                buf += s.recv(1)
                if buf.endswith(self.TERMCHAR_BYTES):
                    break

            resp = buf.decode().strip(self.TERMCHAR)

            if resp.startswith("ERROR"):
                raise RuntimeError(resp)
            else:
                return resp

    def reset(self):
        """Reset SMU paramters to default."""
        self._query("rst")

    @property
    def plf(self):
        """Get the power line frequency in Hz."""
        return float(self._query("plf"))

    @property
    def ch_per_board(self):
        """Get the number of channels per board in use."""
        return int(self._query("cpb"))

    @property
    def maximum_buffer_size(self):
        """Maximum number of samples in write/run/read buffers."""
        return int(self._query("buf"))

    @property
    def num_channels(self):
        """Get the number of connected SMU channels."""
        return int(self._query("chs"))

    @property
    def num_boards(self):
        """Get the number of connected SMU boards."""
        return int(self._query("bds"))

    @property
    def sample_rate(self):
        """Get the raw sample rate for each device."""
        return int(self._query("sr"))

    @property
    def channel_settings(self):
        """Get settings dictionary."""
        return ast.literal_eval(self._query("set"))

    @property
    def nplc(self):
        """Integration time in number of power line cycles."""
        return float(self._query("nplc"))

    @nplc.setter
    def nplc(self, nplc):
        """Set the integration time in number of power line cycles.

        Parameters
        ----------
        nplc : float
            Integration time in number of power line cycles (NPLC).
        """
        self._query(f"nplc {nplc}")

    @property
    def settling_delay(self):
        """Settling delay in seconds."""
        return float(self._query("sd"))

    @settling_delay.setter
    def settling_delay(self, settling_delay):
        """Set the settling delay in seconds.

        Parameters
        ----------
        settling_delay : float
            Settling delay (s).
        """
        self._query(f"sd {settling_delay}")

    @property
    def idn(self):
        """Get SMU id string."""
        return self._query("idn")

    def use_external_calibration(self, channel=None):
        """Use calibration externally to the devices.

        Parameters
        ----------
        channel : int
            Channel number (0-indexed). If `None` apply to all channels.
        """
        self._query(f"cal ext {str(channel)}")

    def use_internal_calibration(self, channel=None):
        """Use calibration internal to the devices.

        Parameters
        ----------
        channel : int or `None`
            Channel number (0-indexed). If `None` apply to all channels.
        """
        self._query(f"cal int {str(channel)}")

    def configure_channel_settings(
        self,
        channel=None,
        four_wire=None,
        v_range=None,
        default=False,
    ):
        """Configure channel.

        Parameters
        ----------
        channel : int
            Channel number (0-indexed). If `None`, apply settings to all channels.
        four_wire : bool
            Four wire enabled.
        v_range : {2.5, 5}
            Voltage range. If 5, channel can output 0-5 V (two quadrant). If 2.5
            channel can output -2.5 - +2.5 V (four quadrant).
        default : bool
            Reset all settings to default.
        """
        if four_wire is not None:
            self._query(f"fw {int(four_wire)} {str(channel)}")

        if v_range is not None:
            self._query(f"vr {v_range} {str(channel)}")

        if default is not None:
            self._query(f"def {int(default)} {str(channel)}")

    def configure_sweep(self, start, stop, points, source_mode="v"):
        """Configure an output sweep for all channels.

        Parameters
        ----------
        start : float
            Starting value in V or A.
        stop : float
            Stop value in V or A.
        points : int
            Number of points in the sweep.
        source_mode : str
            Desired source mode: "v" for voltage, "i" for current.
        """
        self._query(f"swe {start} {stop} {points} {source_mode}")

    def configure_list_sweep(self, values={}, source_mode="v"):
        """Configure list sweeps for all channels.

        All lists must be the same length.

        Parameters
        ----------
        values : dict of lists or list
            Dictionary of lists of source values for sweeps, of the form
            {channel: [source values]}. If a list is given, this list of values will
            be set for all channels.
        source_mode : str
            Desired source mode during measurement: "v" for voltage, "i" for current.
        """
        # strip whitespace from dict, server uses spaces as separator for params in msg
        self._query(f"lst {str(values).replace(' ', '')} {source_mode}")

    def configure_dc(self, values={}, source_mode="v"):
        """Configure a DC output measurement for all channels.

        Parameters
        ----------
        values : dict of float or int; float or int
            Dictionary of output values, of the form {channel: dc_value}. If a value
            of numeric type is given it is applied to all channels.
        source_mode : str
            Desired source mode during measurement: "v" for voltage, "i" for current.
        """
        # strip whitespace from list, server uses spaces as separator for params in msg
        self._query(f"dc {str(values).replace(' ', '')} {source_mode}")

    def measure(self, channels=None, measurement="dc", allow_chunking=False):
        """Perform the configured sweep or dc measurements for all channels.

        Parameters
        ----------
        channels : list of int or int
            List of channel numbers (0-indexed) to measure. If only one channel is
            measured its number can be provided as an int. If `None`, measure all
            channels.
        measurement : {"dc", "sweep"}
            Measurement to perform based on stored settings from configure_sweep
            ("sweep") or configure_dc ("dc", default) method calls.
        allow_chunking : bool
            Allow (`True`) or disallow (`False`) measurement chunking. If a requested
            measurement requires a number of samples that exceeds the size of the
            device buffer this flag will determine whether it gets broken up into
            smaller measurement chunks. If set to `False` and the measurement exceeds
            the buffer size this function will raise a ValueError.

        Returns
        -------
        data : dict
            Data dictionary of the form: {channel: data}.
        """
        return ast.literal_eval(
            self._query(
                f"meas {str(channels).replace(' ', '')} {measurement} "
                + f"{int(allow_chunking)}"
            )
        )

    def enable_output(self, enable, channels=None):
        """Enable/disable channel outputs.

        Paramters
        ---------
        enable : bool
            Turn on (`True`) or turn off (`False`) channel outputs.
        channels : list of int, int, or None
            List of channel numbers (0-indexed). If only one channel is required its
            number can be provided as an int. If `None`, apply to all channels.
        """
        self._query(f"eo {int(enable)} {str(channels).replace(' ', '')}")

    def get_channel_id(self, channel):
        """Get the serial number of requested channel.

        Parameters
        ----------
        channel : int
            Channel number (0-indexed).

        Returns
        -------
        channel_serial : str
            Channel serial string.
        """
        return self._query(f"idn {channel}")

    def set_leds(self, channel=None, R=False, G=False, B=False):
        """Set LED configuration for a channel(s).

        Parameters
        ----------
        channel : int or None
            Channel number (0-indexed). If `None`, apply to all channels.
        R : bool
            Turn on (True) or off (False) the red LED.
        G : bool
            Turn on (True) or off (False) the green LED.
        B : bool
            Turn on (True) or off (False) the blue LED.
        """
        self._query(f"led {int(R)} {int(G)} {int(B)} {str(channel)}")


if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = 2101
    TERMCHAR = "\n"

    with m1kTCPClient(HOST, PORT, TERMCHAR) as smu:
        print(f"SMU ID: {smu.idn}")
