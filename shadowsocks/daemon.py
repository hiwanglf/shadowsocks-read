#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright 2014-2015 clowwindy
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

import os
import sys
import logging
import signal
import time
from shadowsocks import common, shell

# this module is ported from ShadowVPN daemon.c


def daemon_exec(config):
    if 'daemon' in config:
        if os.name != 'posix':
            # 判断系统
            raise Exception('daemon mode is only supported on Unix')
        command = config['daemon']
        if not command:
            command = 'start'
        pid_file = config['pid-file']
        log_file = config['log-file']
        if command == 'start':
            daemon_start(pid_file, log_file)
        elif command == 'stop':
            daemon_stop(pid_file)
            # always exit after daemon_stop
            sys.exit(0)
        elif command == 'restart':
            daemon_stop(pid_file)
            daemon_start(pid_file, log_file)
        else:
            raise Exception('unsupported daemon command %s' % command)


def write_pid_file(pid_file, pid):
    # fcntl: 给文件加锁
    # stat: os.stat是将文件的相关属性读出来，然后用stat模块来处理，处理方式有多重，就要看看stat提供了什么了
    import fcntl
    import stat

    try:
        # os.open()相关文档 https://www.runoob.com/python/os-open.html
        # 打开或者创建一个存放进程pid的文件，并且设置权限，如果失败抛出异常
        fd = os.open(pid_file, os.O_RDWR | os.O_CREAT,
                     stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        shell.print_exception(e)
        return -1

    # 对进程文件加锁，如果有别的程序要加锁，则不能成功，会被阻塞但是不会退出程序，这个锁的类型在文档里面没有找见，奇怪
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    # 如果加锁不成功退出程序
    assert flags != -1
    flags |= fcntl.FD_CLOEXEC
    r = fcntl.fcntl(fd, fcntl.F_SETFD, flags)
    assert r != -1
    # There is no platform independent way to implement fcntl(fd, F_SETLK, &fl)
    # via fcntl.fcntl. So use lockf instead
    # 功能猜测：在创建或者写进程文件的时候进程文件已经被锁，说明程序已经启动或者进程文件已经存在了
    try:
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 0, 0, os.SEEK_SET)
    except IOError:
        # os.read() 方法用于从文件描述符 fd 中读取最多 n 个字节，返回包含读取字节的字符串
        r = os.read(fd, 32)
        if r:
            logging.error('already started at pid %s' % common.to_str(r))
        else:
            logging.error('already started')
        os.close(fd)
        return -1
    # os.ftruncate() 裁剪文件描述符fd对应的文件, 它最大不能超过文件大小。
    os.ftruncate(fd, 0)
    # os.write() 方法用于写入字符串到文件描述符 fd 中. 返回实际写入的字符串长度。
    os.write(fd, common.to_bytes(str(pid)))
    return 0


def freopen(f, mode, stream):
    oldf = open(f, mode)
    oldfd = oldf.fileno()
    newfd = stream.fileno()
    os.close(newfd)
    os.dup2(oldfd, newfd)


def daemon_start(pid_file, log_file):

    def handle_exit(signum, _):
        """

        :param signum: 具体信号
        :param _: 不知道干啥的，存疑，FrameType
        :return: 根据信号判断是否退出进程
        """
        if signum == signal.SIGTERM:
            # 如果进程信号是终止信号，程序退出，sys.exit() 0表示成功退出，1通用错误退出
            sys.exit(0)
        sys.exit(1)

    # signal.signal(sig,action) sig为某个信号，action为该信号的处理函数。
    # signal.SIGINT 中断信号
    signal.signal(signal.SIGINT, handle_exit)
    # signal.SIGTERM 终止信号
    signal.signal(signal.SIGTERM, handle_exit)

    # fork only once because we are sure parent will exit
    # 创建一个子进程，子进程会赋值父进程的数据信息
    # 仅创建一次因为我们确定父进程将会退出
    # 在子进程中返回0，父进程中返回自己成的pid
    pid = os.fork()
    # 检查条件，如果pid不符合就终止程序
    assert pid != -1

    if pid > 0:
        # parent waits for its child
        # 如果是父进程，这里获取的pid大于0，等待子进程彻底完成之后，成功退出。
        time.sleep(5)
        sys.exit(0)

    # child signals its parent to exit
    # 子进程获取父进程的pid
    ppid = os.getppid()
    # 子进程获取自己的pid
    pid = os.getpid()
    if write_pid_file(pid_file, pid) != 0:
        # 如果进程文件创建不成功，终止父进程，中断进程，系统错误退出
        # os.kill 用于直接Kill掉进程
        os.kill(ppid, signal.SIGINT)
        sys.exit(1)

    # 设置新的会话连接
    os.setsid()
    # 简单的忽略给定的信号？？？
    signal.signal(signal.SIG_IGN, signal.SIGHUP)

    print('started')
    # 杀死父进程
    os.kill(ppid, signal.SIGTERM)
    # 关闭标准输入，为了下面的日志打印么？
    sys.stdin.close()
    try:
        # freopen是被包含于C标准库头文件stdio.h中的一个函数，用于重定向输入输出流。
        # 该函数可以在不改变代码原貌的情况下改变输入输出环境，但使用时应当保证流是可靠的。
        # https://blog.csdn.net/s_lisheng/article/details/73799880
        freopen(log_file, 'a', sys.stdout)
        freopen(log_file, 'a', sys.stderr)
    except IOError as e:
        shell.print_exception(e)
        sys.exit(1)


def daemon_stop(pid_file):
    import errno
    try:
        with open(pid_file) as f:
            buf = f.read()
            pid = common.to_str(buf)
            if not buf:
                logging.error('not running')
    except IOError as e:
        shell.print_exception(e)
        if e.errno == errno.ENOENT:
            # always exit 0 if we are sure daemon is not running
            logging.error('not running')
            return
        sys.exit(1)
    pid = int(pid)
    if pid > 0:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                logging.error('not running')
                # always exit 0 if we are sure daemon is not running
                return
            shell.print_exception(e)
            sys.exit(1)
    else:
        logging.error('pid is not positive: %d', pid)

    # sleep for maximum 10s
    for i in range(0, 200):
        try:
            # query for the pid
            os.kill(pid, 0)
        except OSError as e:
            if e.errno == errno.ESRCH:
                break
        time.sleep(0.05)
    else:
        logging.error('timed out when stopping pid %d', pid)
        sys.exit(1)
    print('stopped')
    os.unlink(pid_file)


def set_user(username):
    if username is None:
        return

    import pwd
    import grp

    try:
        pwrec = pwd.getpwnam(username)
    except KeyError:
        logging.error('user not found: %s' % username)
        raise
    user = pwrec[0]
    uid = pwrec[2]
    gid = pwrec[3]

    cur_uid = os.getuid()
    if uid == cur_uid:
        return
    if cur_uid != 0:
        logging.error('can not set user as nonroot user')
        # will raise later

    # inspired by supervisor
    if hasattr(os, 'setgroups'):
        groups = [grprec[2] for grprec in grp.getgrall() if user in grprec[3]]
        groups.insert(0, gid)
        os.setgroups(groups)
    os.setgid(gid)
    os.setuid(uid)
