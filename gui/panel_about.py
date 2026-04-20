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

# load libs
import wx

from . import config, images, mwx

# load modules
from .ids import *

# ABOUT mMass PANEL
# -----------------

if wx.Platform == "__WXMAC__":
    frame = wx.Frame
    frameTitle = ""
else:
    frame = wx.MiniFrame
    frameTitle = "About mMass"


class panelAbout(frame):
    """About mMass."""

    def __init__(self, parent: wx.Window) -> None:
        frame.__init__(
            self,
            parent,
            -1,
            frameTitle,
            style=wx.DEFAULT_FRAME_STYLE
            & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX),
        )
        self.parent = parent

        # make gui items
        sizer = self.makeGUI()
        self.Bind(wx.EVT_CLOSE, self.onClose)

        # fit layout
        self.Layout()
        sizer.Fit(self)
        self.SetSizer(sizer)
        self.SetMinSize(self.GetSize())
        self.Centre()

    # ----

    def makeGUI(self) -> wx.Sizer:
        """Make panel gui."""

        # make elements
        panel = wx.Panel(self, -1)

        image = wx.StaticBitmap(panel, -1, images.lib["iconAbout"])

        title = wx.StaticText(panel, -1, "mMass")
        title.SetFont(
            wx.Font(
                mwx.NORMAL_FONT_SIZE,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_BOLD,
            )
        )

        versionLabel = f"Version {config.version}"
        if config.nightbuild:
            versionLabel = f"{versionLabel} ({config.nightbuild})\nFor testing only!"
        version = wx.StaticText(panel, -1, versionLabel, style=wx.ALIGN_CENTRE)
        version.SetFont(wx.SMALL_FONT)

        copyright = wx.StaticText(panel, -1, "(c) 2005-2013 Martin Strohalm")
        copyright.SetFont(wx.SMALL_FONT)

        homepage_butt = wx.Button(panel, ID_helpHomepage, "Homepage", size=(150, -1))
        homepage_butt.Bind(wx.EVT_BUTTON, self.parent.onLibraryLink)

        donate_butt = wx.Button(panel, ID_helpDonate, "Make a Donation", size=(150, -1))
        donate_butt.Bind(wx.EVT_BUTTON, self.parent.onLibraryLink)

        cite_butt = wx.Button(panel, ID_helpCite, "How to Cite", size=(150, -1))
        cite_butt.Bind(wx.EVT_BUTTON, self.parent.onLibraryLink)

        # pack elements into panel sizer
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(image, 0, wx.CENTER | wx.ALL, 20)
        panel_sizer.Add(title, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 20)
        panel_sizer.AddSpacer(10)
        panel_sizer.Add(version, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 20)
        panel_sizer.AddSpacer(10)
        panel_sizer.Add(copyright, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 20)
        panel_sizer.AddSpacer(20)
        panel_sizer.Add(homepage_butt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 20)
        panel_sizer.AddSpacer(10)
        panel_sizer.Add(donate_butt, 0, wx.CENTER | wx.LEFT | wx.RIGHT, 20)
        panel_sizer.AddSpacer(10)
        panel_sizer.Add(cite_butt, 0, wx.CENTER | wx.LEFT | wx.RIGHT | wx.BOTTOM, 20)

        panel.SetSizer(panel_sizer)

        # pack panel into frame sizer
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(panel, 1, wx.EXPAND)

        return main_sizer

    # ----

    def onClose(self, evt: wx.Event) -> None:
        """Destroy this frame."""
        self.Destroy()

    # ----
