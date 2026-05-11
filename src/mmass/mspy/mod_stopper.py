# -------------------------------------------------------------------------
#     Copyright (C) 2005-2013 Martin Strohalm <www.mmass.org>

#     This program is free software; you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation; either version 3 of the License, or
#     (at your option) any later version.

#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#     GNU General Public License for more details.

#     Complete text of GNU GPL can be found in the file LICENSE.TXT in the
#     main directory of the program.
# -------------------------------------------------------------------------

# stop exception
class ForceQuitError(Exception):
    """Force quit all processing."""

    pass


# define stopper class
class Stopper:
    """Deffinition of processing stopper class."""

    def __init__(self) -> None:
        self.value = False

    def __bool__(self) -> bool:
        return self.value

    def __repr__(self) -> str:
        return str(self.value)

    def enable(self) -> None:
        self.value = True

    def disable(self) -> None:
        self.value = False

    def check(self) -> None:
        if self.value:
            self.value = False
            raise ForceQuitError


# init stopper
STOPPER = Stopper()
CHECK_FORCE_QUIT = STOPPER.check


# mspy stopper functions
def stop() -> None:
    """Set stopper to stop."""
    STOPPER.enable()


def start() -> None:
    """Set stopper to start."""
    STOPPER.disable()
