# BSD 3-Clause License
#
# Copyright (c) 2022-2025, rd2
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import inspect

from dataclasses import dataclass

@dataclass(frozen=True)
class _CN:
    DEBUG = 1
    INFO  = 2
    WARN  = 3
    ERROR = 4
    FATAL = 5
CN = _CN()

_tag = ("",
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "FATAL")

_msg = ("",
        "Debugging ...",
        "Success! No errors, no warnings",
        "Partial success, raised non-fatal warnings",
        "Partial success, encountered non-fatal errors",
        "Failure, triggered fatal errors")

_logs   = []
_level  = CN.INFO
_status = 0


def logs():
    """Returns the logs list."""
    return _logs


def level():
    """Returns current log level."""
    return _level


def status():
    """Returns current log status."""
    return _status


def is_debug():
    """Returns whether current status is DEBUG."""
    return bool(_status == CN.DEBUG)


def is_info():
    """Returns whether current status is INFO."""
    return bool(_status == CN.INFO)


def is_warn():
    """Returns whether current status is WARNING."""
    return bool(_status == CN.WARNING)


def is_error():
    """Returns whether current status is ERROR."""
    return bool(_status == CN.ERROR)


def is_fatal():
    """Returns whether current status is FATAL."""
    return bool(_status == CN.FATAL)


def tag(lvl=_level):
    """Returns preset OSlg string that matches log level."""
    try:
        lvl = int(lvl)
    except ValueError as e:
        return _tag[0]

    if not 0 <= lvl < len(_tag):
        return _tag[0]

    return _tag[lvl]


def msg(stat=_status):
    """Returns preset OSlg message that matches log status."""
    try:
        stat = int(stat)
    except ValueError as e:
        return _msg[0]

    if not 0 <= stat < len(_msg):
        return _msg[0]

    return _msg[stat]


def trim(txt="", length=60):
    """Converts object to String - trims if necessary."""
    try:
        length = int(length)
    except ValueError as e:
        length = 60

    try:
        txt = str(txt).strip()[:length]
    except UnicodeEncodeError:
        txt = ""
    except Exception as e:
        txt = ""

    return txt


def reset(lvl=CN.DEBUG):
    """Resets level, if lvl (input) is within accepted range."""
    global _level

    try:
        lvl = int(lvl)
    except ValueError as e:
        return _level

    if CN.DEBUG <= lvl <= CN.FATAL:
        _level = lvl

    return _level


def log(lvl=CN.DEBUG, message=""):
    """Logs a new entry, if provided arguments are valid."""
    global _status
    global _logs

    try:
        lvl = int(lvl)
    except ValueError as e:
        return _status

    message = trim(message)

    if not message or lvl < CN.DEBUG or lvl > CN.FATAL or lvl < _level:
        return _status

    if lvl > _status:
        _status = lvl

    _logs.append(dict(level=lvl, message=message))

    return _status


def invalid(id="", mth="", ord=0, lvl=CN.DEBUG, res=None):
    """Logs template 'invalid object' message (~60chars), if valid arguments."""
    id  = trim(id)
    mth = trim(mth)

    try:
        ord = int(ord)
    except ValueError as e:
        return res

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    msg = "Invalid '%s' " % (id)

    if ord > 0:
        msg += "arg #%d "  % (ord)

    msg += "(%s)" % (mth)
    log(lvl, msg)

    return res


def mismatch(id="", obj=None, cl=None, mth="", lvl=CN.DEBUG, res=None):
    """Logs template 'instance/class mismatch' message, if valid arguments."""

    id  = trim(id)
    mth = trim(mth)

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not inspect.isclass(cl) or isinstance(obj, cl):
        return res
    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    msg  = "'%s' %s? " % (id, type(obj).__name__)
    msg += "expecting %s (%s)" % (cl.__name__, mth)
    log(lvl, msg)

    return res


def hashkey(id="", dct={}, key="", mth="", lvl=CN.DEBUG, res=None):
    """Logs template 'missing hash key' message, if valid arguments."""

    id  = trim(id)
    mth = trim(mth)
    ky  = trim(key)

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not isinstance(dct, dict) or key in dct:
        return res
    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    log(lvl, "Missing '%s' key in %s (%s)" % (ky, id, mth))

    return res


def empty(id="", mth="", lvl=CN.DEBUG, res=None):
    """Logs template 'empty' message, if provided arguments are valid."""

    id  = trim(id)
    mth = trim(mth)

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    log(lvl, "Empty '%s' (%s)" % (id, mth))

    res


def zero(id="", mth="", lvl=CN.DEBUG, res=None):
    """Logs template 'zero' value message, if provided arguments are valid."""

    id  = trim(id)
    mth = trim(mth)

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    log(lvl, "Zero '%s' (%s)" % (id, mth))

    return res


def negative(id="", mth="", lvl=CN.DEBUG, res=None):
    """Logs template 'negative' message, if provided arguments are valid."""

    id  = trim(id)
    mth = trim(mth)

    try:
        lvl = int(lvl)
    except ValueError as e:
        return res

    if not id or not mth or lvl < CN.DEBUG or lvl > CN.FATAL:
        return res

    log(lvl, "Negative '%s' (%s)" % (id, mth))

    return res


def clean():
    """Resets log status and entries."""
    global _status
    global _logs

    _status = 0
    _logs   = []

    return _level
