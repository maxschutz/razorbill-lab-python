#
# Copyright 2016-2021 Razorbill Instruments Ltd.
# This file is part of the Razorbill Lab Python library which is
# available under the MIT licence - see the LICENCE file for more.
#
"""
Module for capaNCDT controllers and demodulators. Requires MEDAQLib.
"""

from . import _Sensor, _Channel

class _DT6xxx_Channel(_Channel):
    pass

class _DT6xxx(_Sensor):
    """ Bae class for DT62xx, DT65xx and KSS64xx. Subclass it."""
    def __init__(self, address, num_channels=1):
        super().__init__(address)
        self.channels = {}
        for i in range(num_channels+1):
            self.channels[i]=_DT6xxx_Channel(self._lib, i, num_channels, self._handle)
    
    def _set_average_type(self, average_type):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_AvrType') 
        self._lib.set_parameter_int(self._handle, 'SP_AvrType', average_type) 
        self._lib.sensor_command(self._handle)
    
    def _get_average_type(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_AvrType') 
        self._lib.sensor_command(self._handle)
        return self._lib.get_parameter_int(self._handle, 'SA_AvrType') 
    
    average_type = property(fset=_set_average_type, fget=_get_average_type,
                            doc="0: Off, 1: Moving Avg, 2: Mean, 3: Median, 4: Dynamic")
    
    def _set_average_num(self, average_num):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_AvrNbr') 
        self._lib.set_parameter_int(self._handle, 'SP_AvrNbr', average_num) 
        self._lib.sensor_command(self._handle)
    
    def _get_average_num(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_AvrNbr') 
        self._lib.sensor_command(self._handle)
        return self._lib.get_parameter_int(self._handle, 'SA_AvrNbr') 
    
    average_num = property(fset=_set_average_num, fget=_get_average_num,
                           doc="Number of points used in averaging, 2<=n<=8")
    
    def _get_frames_avail(self):
        data_avail = self._lib.data_available(self._handle)
        return int(data_avail / self._frame_size)
        
    frames_available = property(fget=_get_frames_avail,
                                doc="Number of measurement frames in the buffer")

class DT62xx(_DT6xxx):
    """Class for DT6200 series controllers and demodulators 
    
    There are a variety of properties which change settings on the instrument.
    Most of these affect all channels. Not all properties can be changed
    through this module, you can use the web interface at the same time.
    
    To get one data point, use:
        instrument.ch[1].poll
    this will return the most recent measurement on channel 1, and will not 
    remove it from the internal data buffer, so it will still be available 
    to get_data_block.
    ch[0].poll can also be used, it will return a 4-element list, with 
    simultaneous measurements from all four channels.
    
    To get blocks of data use
        instrument.get_data_block()
    this will remove the data from the internal buffer. If this is not called
    for some time, the data buffer may overflow, data will be lost, and a
    warning logged next time this or frames_available is used. To avoid the 
    warning, call flush_buffer just before starting to get useful data, and
    get_data_block every few minutes until you have all the data you need.
    
    """
    def __init__(self, address, num_channels=1):
        self._name = 'CONTROLLER_DT6200'
        super().__init__(address, num_channels)
        self._frame_size = num_channels
    
    def _set_analog_lp(self, enabled):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_AnalogLowPass') 
        self._lib.set_parameter_int(self._handle, 'SP_LowPass', int(enabled)) 
        self._lib.sensor_command(self._handle)
    
    def _get_analog_lp(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_AnalogLowPass') 
        self._lib.sensor_command(self._handle)
        return bool(self._lib.get_parameter_int(self._handle, 'SA_LowPass'))
    
    analog_lp_enabled = property(fset=_set_analog_lp, fget=_get_analog_lp,
                                 doc="Boolean, enable or disable analog filter")
    
    def _set_measure_time(self, value):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_SampleTime') 
        self._lib.set_parameter_double(self._handle, 'SP_SampleTime', value)
        self._lib.sensor_command(self._handle)
        self._lib.clear_parameters(self._handle)
    
    def _get_measure_time(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_SampleTime') 
        self._lib.sensor_command(self._handle)
        return self._lib.get_parameter_double(self._handle, 'SA_SampleTime')
    
    measure_time = property(fset=_set_measure_time, fget=_get_measure_time,
                            doc="Measurement time in us. Gets coerced to allowable value.")
    
    def get_data_block(self, num_frames=None):
        """Get data from the buffer. Defaults to all available frames if
           num_frames is not set or is None. Returns a list of lists, with each
           inner list containing sensor readings.
           Frame size may be dynamically inferred from 0.0 markers.
           Missing demodulators return zero.
        """
        # Determine the number of raw data points to fetch.
        # If num_frames is None, fetch all available data points.
        # Otherwise, fetch enough points for the requested number of frames based on the current _frame_size.
        # This initial fetch count is an estimate if the frame size is later re-evaluated from data.
        if num_frames is None:
            points_to_fetch = self._lib.data_available(self._handle)
            if points_to_fetch == 0:
                return []
        else:
            if self._frame_size <= 0: # Initial _frame_size must be valid
                raise ValueError("Initial _frame_size must be positive when num_frames is specified.")
            points_to_fetch = self._frame_size * num_frames
            if points_to_fetch == 0: # Handles num_frames = 0 or _frame_size = 0 if not caught above
                return []

        raw_data = self._lib.data_transfer(self._handle, points_to_fetch)

        if not raw_data:
            return [] # No data transferred

        # Requirement: "if there are two 0.0 in a row, throw an error".
        # This check should be done on the fetched raw_data.
        if len(raw_data) > 1:
            for i in range(len(raw_data) - 1):
                if raw_data[i] == 0.0 and raw_data[i+1] == 0.0:
                    raise ValueError("Consecutive 0.0 values detected in raw data stream, indicating an error.")

        # Interpretation of comments and user request:
        # 1. "if the underlying data is 0.0 its a missing demodulator..."
        #    -> 0.0 is a data value.
        # 2. "if there is 0.0, that indicates the start of a new frame."
        # 3. User: "if i see a 0.0 i set my frame size to how big the spacing between 0.0 is"
        #    -> This implies 0.0s are periodic markers for the start of frames,
        #       and their spacing defines the actual frame size.
        
        effective_frame_size = self._frame_size # Default to configured frame size

        zero_indices = [i for i, val in enumerate(raw_data) if val == 0.0]

        if len(zero_indices) > 1:
            # At least two 0.0 markers found. Calculate spacings between them.
            # These spacings are potential frame sizes.
            spacings = [zero_indices[j+1] - zero_indices[j] for j in range(len(zero_indices)-1)]
            
            # If all spacings are consistent and positive, this is the new effective frame size.
            if spacings and all(s == spacings[0] for s in spacings) and spacings[0] > 0:
                effective_frame_size = spacings[0]
                # Optional: To make this change persistent for the instance, you could update self._frame_size:
                # self._frame_size = effective_frame_size 
        # If zero_indices has 0 or 1 elements, or if spacings are inconsistent,
        # we stick with the original self._frame_size (or the one from __init__) as effective_frame_size.
        
        if effective_frame_size <= 0:
            raise ValueError(f"Determined frame size ({effective_frame_size}) is not positive. Check instrument setup or num_channels.")

        # Now, frame the raw_data using the effective_frame_size.
        output_frames = []
        for i in range(0, len(raw_data), effective_frame_size):
            frame = raw_data[i : i + effective_frame_size]
            # Only add full frames. Partial frames at the end are ignored to ensure data integrity.
            if len(frame) == effective_frame_size:
                output_frames.append(frame)
            # else:
            #     if len(frame) > 0:
            #         # You might want to log or handle partial frames differently.
            #         # print(f"Warning: Discarding partial frame of length {len(frame)} at the end of data stream.")

        # If num_frames was specified, return at most that many frames.
        # The actual number of frames parsed might differ from the request if effective_frame_size
        # changed from the initial _frame_size used for points_to_fetch calculation.
        if num_frames is not None:
            return output_frames[:num_frames]
        else:
            return output_frames

    
    def flush_buffer(self):
        """
        Clears the data buffer in the library.
        """
        self._lib.flush_buffer(self._handle)

class DT65xx(_DT6xxx):
    """Class for DT6500 series controllers and demodulators 
    
    There are a variety of properties which change settings on the instrument.
    Most of these affect all channels. Not all properties can be changed
    through this module, you can use the web interface at the same time.
    
    To get one data point, use:
        instrument.ch[1].poll
    this will return the most recent measurement on channel 1, and will not 
    remove it from the internal data buffer, so it will still be available 
    to get_data_block.
    ch[0].poll can also be used, it will return a 8-element list, with 
    simultaneous measurements from all eight channels.
    
    To get blocks of data use
        instrument.get_data_block()
    this will remove the data from the internal buffer. If this is not called
    for some time, the data buffer may overflow, data will be lost, and a
    warning logged next time this or frames_available is used. To avoid the 
    warning, call flush_buffer just before starting to get useful data, and
    get_data_block every few minutes until you have all the data you need.
    
    """
    def __init__(self, address, num_channels=1):
        self._name = 'CONTROLLER_DT6500'
        super().__init__(address, num_channels)
        self._frame_size = num_channels
    
    def _set_analog_lp(self, enabled):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_AnalogLowPass') 
        self._lib.set_parameter_int(self._handle, 'SP_LowPass', int(enabled)) 
        self._lib.sensor_command(self._handle)
    
    def _get_analog_lp(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_AnalogLowPass') 
        self._lib.sensor_command(self._handle)
        return bool(self._lib.get_parameter_int(self._handle, 'SA_LowPass'))
    
    analog_lp_enabled = property(fset=_set_analog_lp, fget=_get_analog_lp,
                                 doc="Boolean, enable or disable analog filter")
    
    def _set_measure_time(self, value):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Set_SampleTime') 
        self._lib.set_parameter_double(self._handle, 'SP_SampleTime', value)
        self._lib.sensor_command(self._handle)
        self._lib.clear_parameters(self._handle)
    
    def _get_measure_time(self):
        self._lib.set_parameter_string(self._handle, 'S_Command', 'Get_SampleTime') 
        self._lib.sensor_command(self._handle)
        return self._lib.get_parameter_double(self._handle, 'SA_SampleTime')
    
    measure_time = property(fset=_set_measure_time, fget=_get_measure_time,
                            doc="Measurement time in us. Gets coerced to allowable value.")
    
    def get_data_block(self, num_frames=None):
        """Get data from the buffer. Defaults to all available frames if
           num_frames is not set or is None. Returns a list of lists, with each
           inner list containing all four sensor readings. If converted to a
           numpy array, each sensor gets a column. Missing demodulators return
           zero, missing sensors return about 5% over max range.
        """
        if num_frames == None:
            num_frames = self.frames_available
        data = self._lib.data_transfer(self._handle, self._frame_size * num_frames)
        return [data[i:i+self._frame_size] for i in range(0,len(data),self._frame_size)]
    
    def flush_buffer(self):
        """
        Clears the data buffer in the library.
        """
        self._lib.flush_buffer(self._handle)