# Copyright 2009 One Laptop Per Child
# Author: Sayamindu Dasgupta <sayamindu@laptop.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import Icon
from sugar3.graphics.xocolor import XoColor
from sugar3 import profile
from sugar3.util import timestamp_to_elapsed_string
from sugar3.graphics import style

from readdialog import BookmarkAddDialog, BookmarkEditDialog

from gettext import gettext as _


_logger = logging.getLogger('read-activity')

# TODO: Add support for multiple bookmarks in a single page
# (required when sharing)


class BookmarkView(Gtk.EventBox):

    __gsignals__ = {
        'bookmark-changed': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE,
                             ([])),
    }

    def __init__(self):
        Gtk.EventBox.__init__(self)
        self.set_size_request(style.GRID_CELL_SIZE,
                              style.GRID_CELL_SIZE * 2)
        self._xo_color = profile.get_color()
        self._fill_color = style.Color(self._xo_color.get_fill_color())
        self._stroke_color = style.Color(self._xo_color.get_stroke_color())

        self._box = Gtk.VButtonBox()
        self._box.set_layout(Gtk.ButtonBoxStyle.CENTER)
        self.add(self._box)
        self._box.show()

        self._bookmark_icon = None
        self._bookmark_manager = None
        self._is_showing_local_bookmark = False
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self._box.connect('draw', self.__draw_cb)

    def __draw_cb(self, widget, ctx):
        width = style.GRID_CELL_SIZE
        height = style.GRID_CELL_SIZE * 2

        ctx.rectangle(0, 0, width, height)
        ctx.set_source_rgba(*self._fill_color.get_rgba())
        ctx.paint()

        ctx.new_path()
        ctx.move_to(0, 0)
        ctx.line_to(width, 0)
        ctx.line_to(width, height)
        ctx.line_to(width / 2, height - width / 2)
        ctx.line_to(0, height)
        ctx.close_path()
        ctx.set_source_rgba(*self._stroke_color.get_rgba())
        ctx.fill()

    def _add_bookmark_icon(self, bookmark):
        xocolor = XoColor(str(bookmark.color))
        self._bookmark_icon = Icon(icon_name='emblem-favorite',
                                   xo_color=xocolor,
                                   pixel_size=style.STANDARD_ICON_SIZE)

        self._box.props.has_tooltip = True
        self.__box_query_tooltip_cb_id = self._box.connect(
            'query_tooltip', self.__bookmark_icon_query_tooltip_cb, bookmark)

        self.__event_cb_id = \
            self.connect('event', self.__event_cb, bookmark)

        self._box.pack_start(self._bookmark_icon, False, False, 0)
        self._bookmark_icon.show_all()

        if bookmark.is_local():
            self._is_showing_local_bookmark = True

    def __bookmark_icon_query_tooltip_cb(self, widget, x, y, keyboard_mode,
                                         tip, bookmark):
        tooltip_header = bookmark.get_note_title()
        tooltip_body = bookmark.get_note_body()
        time = timestamp_to_elapsed_string(bookmark.timestamp)
        #TRANS: This goes like Bookmark added by User 5 days ago
        #TRANS: (the elapsed string gets translated automatically)
        tooltip_footer = (
            _('Bookmark added by %(user)s %(time)s')
            % {'user': bookmark.nick.decode('utf-8'),
               'time': time.decode('utf-8')})

        vbox = Gtk.VBox()

        l = Gtk.Label('<big>%s</big>' % tooltip_header)
        l.set_use_markup(True)
        l.set_width_chars(40)
        l.set_line_wrap(True)
        vbox.pack_start(l, False, False, 0)
        l.show()

        l = Gtk.Label('%s' % tooltip_body)
        l.set_use_markup(True)
        l.set_alignment(0, 0)
        l.set_padding(2, 6)
        l.set_width_chars(40)
        l.set_line_wrap(True)
        l.set_justify(Gtk.Justification.FILL)
        vbox.pack_start(l, True, True, 0)
        l.show()

        l = Gtk.Label('<small><i>%s</i></small>' % tooltip_footer)
        l.set_use_markup(True)
        l.set_width_chars(40)
        l.set_line_wrap(True)
        vbox.pack_start(l, False, False, 0)
        l.show()

        tip.set_custom(vbox)

        return True

    def __event_cb(self, widget, event, bookmark):
        if event.type == Gdk.EventType.BUTTON_PRESS and \
                self._bookmark_icon is not None:

            bookmark_title = bookmark.get_note_title()
            bookmark_content = bookmark.get_note_body()

            dialog = BookmarkEditDialog(
                parent_xid=self.get_toplevel().get_window(),
                dialog_title=_("Add notes for bookmark: "),
                bookmark_title=bookmark_title,
                bookmark_content=bookmark_content, page=bookmark.page_no,
                sidebarinstance=self)
            dialog.show_all()

        return False

    def _clear_bookmarks(self):
        for bookmark_icon in self._box.get_children():
            self._box.disconnect(self.__box_query_tooltip_cb_id)
            self.disconnect(self.__event_cb_id)

            bookmark_icon.hide()  # XXX: Is this needed??
            bookmark_icon.destroy()

            self._bookmark_icon = None

            self._is_showing_local_bookmark = False

    def set_bookmarkmanager(self, bookmark_manager):
        self._bookmark_manager = bookmark_manager

    def get_bookmarkmanager(self):
        return (self._bookmark_manager)

    def update_for_page(self, page):

        self._clear_bookmarks()
        if self._bookmark_manager is None:
            return

        bookmarks = self._bookmark_manager.get_bookmarks_for_page(page)

        if bookmarks:
            self.show()
        else:
            self.hide()

        for bookmark in bookmarks:
            self._add_bookmark_icon(bookmark)
        self.notify_bookmark_change()

    def notify_bookmark_change(self):
        self.emit('bookmark-changed')

    def add_bookmark(self, page):
        bookmark_title = (_("%s's bookmark") % profile.get_nick_name())
        bookmark_content = (_("Bookmark for page %d") % (int(page) + 1))
        dialog = BookmarkAddDialog(
            parent_xid=self.get_toplevel().get_window(),
            dialog_title=_("Add notes for bookmark: "),
            bookmark_title=bookmark_title,
            bookmark_content=bookmark_content, page=page,
            sidebarinstance=self)
        dialog.show_all()

    def _real_add_bookmark(self, page, content):
        self._bookmark_manager.add_bookmark(page, unicode(content))
        self.update_for_page(page)

    def del_bookmark(self, page):
        self._bookmark_manager.del_bookmark(page)
        self.update_for_page(page)

    def is_showing_local_bookmark(self):
        return self._is_showing_local_bookmark
