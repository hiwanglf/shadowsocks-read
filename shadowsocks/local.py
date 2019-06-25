#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2012-2015 clowwindy
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    with_statement

import sys
import os
import logging
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))
from shadowsocks import shell, daemon, eventloop, tcprelay, udprelay, asyncdns


def main():
    shell.check_python()    # 判断python版本

    # fix py2exe
    # hasattr(object, name) 判断一个对象里面是否有name属性或者name方法，返回BOOL值，有name特性返回True， 否则返回False。
    if hasattr(sys, "frozen") and sys.frozen in \
            ("windows_exe", "console_exe"):
        # sys.executable python可执行文件的绝对路径
        # os.path.abspath(path) 返回绝对路径
        # os.path.dirname(path) 返回文件路径
        # os.chdir() 用于改变当前工作目录到指定的路径
        p = os.path.dirname(os.path.abspath(sys.executable))
        os.chdir(p)

    # 获取配置字典，包含每个配置项的具体配置值
    config = shell.get_config(True)

    daemon.daemon_exec(config)

    try:
        logging.info("starting local at %s:%d" %
                     (config['local_address'], config['local_port']))

        dns_resolver = asyncdns.DNSResolver()
        tcp_server = tcprelay.TCPRelay(config, dns_resolver, True)
        udp_server = udprelay.UDPRelay(config, dns_resolver, True)
        loop = eventloop.EventLoop()
        dns_resolver.add_to_loop(loop)
        tcp_server.add_to_loop(loop)
        udp_server.add_to_loop(loop)

        def handler(signum, _):
            logging.warn('received SIGQUIT, doing graceful shutting down..')
            tcp_server.close(next_tick=True)
            udp_server.close(next_tick=True)
        signal.signal(getattr(signal, 'SIGQUIT', signal.SIGTERM), handler)

        def int_handler(signum, _):
            sys.exit(1)
        signal.signal(signal.SIGINT, int_handler)

        daemon.set_user(config.get('user', None))
        loop.run()
    except Exception as e:
        shell.print_exception(e)
        sys.exit(1)

if __name__ == '__main__':
    main()
