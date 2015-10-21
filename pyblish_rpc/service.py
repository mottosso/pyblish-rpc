
# Standard library
import os
import sys
import time
import getpass
import logging
import traceback

# Pyblish Library
import pyblish.api
import pyblish.lib
import pyblish.plugin

# Local Library
import version
import mocking
import formatting

_log = logging.getLogger("pyblish-rpc")


class RpcService(object):
    _count = 0
    _instances = property(
        lambda self: pyblish.lib.ItemList("name", self._context))

    def __init__(self):
        self._context = None
        self._plugins = None
        self._provider = None

        self.reset()

    def test(self, vars):
        test = pyblish.logic.registered_test()
        return test(**vars)

    def ping(self):
        """Used to check connectivity"""
        return {
            "message": "Hello, whomever you are"
        }

    def stats(self):
        """Return statistics about the API"""
        return {
            "totalRequestCount": self._count,
        }

    def reset(self):
        self._context = pyblish.api.Context()
        self._plugins = pyblish.api.discover()
        self._provider = pyblish.plugin.Provider()

    def context(self):
        # Append additional metadata to context
        port = os.environ.get("PYBLISH_CLIENT_PORT", -1)
        hosts = ", ".join(reversed(pyblish.api.registered_hosts()))

        for key, value in {"host": hosts,
                           "port": int(port),
                           "user": getpass.getuser(),
                           "connectTime": pyblish.lib.time(),
                           "pyblishServerVersion": pyblish.version,
                           "pyblishRPCVersion": version.version,
                           "pythonVersion": sys.version}.iteritems():

            self._context.set_data(key, value)

        return formatting.format_context(self._context)

    def discover(self):
        return formatting.format_plugins(self._plugins)

    def process(self, plugin, instance=None, action=None):
        """Given JSON objects from client, perform actual processing

        Arguments:
            plugin (dict): JSON representation of plug-in to process
            instance (dict, optional): JSON representation of Instance to
                be processed.
            action (str, optional): Id of action to process

        """

        plugin_obj = self._plugin_from_name(plugin["name"])
        instance_obj = (self._instances[instance["name"]]
                        if instance is not None else None)

        result = pyblish.plugin.process(
            plugin=plugin_obj,
            context=self._context,
            instance=instance_obj,
            action=action)

        return formatting.format_result(result)

    def repair(self, plugin, instance=None):
        plugin_obj = self._plugin_from_name(plugin["name"])
        instance_obj = (self._instances[instance["name"]]
                        if instance is not None else None)

        result = pyblish.plugin.repair(
            plugin=plugin_obj,
            context=self._context,
            instance=instance_obj)

        return formatting.format_result(result)

    def _dispatch(self, method, params):
        """Customise exception handling"""
        self._count += 1

        func = getattr(self, method)
        try:
            return func(*params)
        except Exception as e:
            traceback.print_exc()
            raise e

    def _plugin_from_name(self, name):
        """Parse plug-in id to object"""
        plugins = pyblish.lib.ItemList("__name__", self._plugins)
        return plugins[name]


class MockRpcService(RpcService):
    def __init__(self, delay=0.01, *args, **kwargs):
        super(MockRpcService, self).__init__(*args, **kwargs)

        self.delay = delay

    def discover(self):
        return formatting.format_plugins(mocking.plugins)

    def process(self, *args, **kwargs):
        time.sleep(self.delay)
        return super(MockRpcService, self).process(*args, **kwargs)

    @classmethod
    def _plugin_from_name(cls, name):
        """Parse plug-in id to object"""
        plugins = pyblish.lib.ItemList("__name__", mocking.plugins)
        return plugins[name]
