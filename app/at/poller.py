import time
import logging
import threading
import serial
import io
import importlib
import inspect
import statsd
from .command import Command

logger = logging.getLogger(__name__)

class Poller:
    """
    Polls a serial port with AT commands, collecting responses.
    """

    def __init__(self, dev, poll_delay, statsd_config=None):
        """
        Create a new poller.
        """

        # The path to the quectel_CM binary
        self.dev = dev

        # The delay in ms between polls
        self.poll_delay = poll_delay

        # Are we polling periodically?
        self.is_polling = False

        # Send polled data to StatsD?
        self.statsd_client = None
        if statsd_config is not None and 'host' in statsd_config:
            try:
                self.statsd_client = statsd.StatsClient(
                    statsd_config['host'],
                    statsd_config['port'] if 'port' in statsd_config else 8125, prefix='quectel_cpe'
                )
            except Exception as statsd_err:
                logger.warn("Could not connect to statsd host %s: %s" % (statsd_config['host'], statsd_err))

        # Import all the command classes
        self.commands = []
        for command_name, command_class in inspect.getmembers(
            importlib.import_module('at.commands')
        ):

            # If this is the class we are looking for...
            if inspect.isclass(command_class) and issubclass(command_class, Command):

                # Don't render the base StatusCheck itself though
                if command_class != Command:
                    logger.info('registering command class %s' % command_class)
                    self.commands.append(command_class())

        # The thread on which the serial port sending will be performed
        self.__poll_thread = threading.Thread(target=self.__poll)
        self.__poll_thread.daemon = True

    def start(self):
        """
        Start polling
        """
        logger.info("Starting AT command polling @ %s" % self.dev)
        self.is_polling = True
        self.__poll_thread.start()

    def stop(self):
        """
        Stop polling
        """
        self.is_polling = False

    def __poll(self):
        """
        The main poll loop.
        """
        self.is_polling = True

        try:

            # While we've not been terminated
            while self.is_polling:

                logger.info("Opening serial port %s..." % self.dev)
                at_handle = serial.Serial(self.dev, 115200, timeout=3)
                
                # While connected...
                while True:

                    # Wait the poll delay
                    time.sleep(self.poll_delay / 1000)
                    try:
                        # Poll each of the registered AT commands
                        for command in self.commands:
                            
                            # Collect results from the command
                            command.poll(at_handle)

                            if self.statsd_client is not None:
                                for result in command.results:
                                    try:
                                        self.statsd_client.gauge(result.key, float(result.value) if '.' in result.value else int(result.value))
                                        logger.info("dispatch to statsd: %s -> %s" % (result.key, result.value))
                                    except:
                                        pass

                    except Exception as serial_error:
                        logger.error("Serial comms error: %s" % serial_error)
                        try:
                            at_handle.close()
                        except:
                            pass
                        break

        except Exception as poll_ex:
            logger.error('Error polling AT interface %s: %s' % (self.dev, poll_ex))
            raise poll_ex
