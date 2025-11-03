#!/usr/bin/env python3
import gi, subprocess, signal, threading, pexpect

gi.require_version('AyatanaAppIndicator3', '0.1')
gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import AyatanaAppIndicator3 as AppIndicator3, Gtk, GLib, Notify

APP_ID = "vpn_indicator"
last_status = None

# --- VPN control functions ---
def run_command(cmd):
    """Run a simple command (used for disconnect)."""
    def _worker():
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            print(f"Error running {cmd}: {e}")
    threading.Thread(target=_worker, daemon=True).start()

def on_connect(_):
    dialog = Gtk.Dialog(title="SNX Connect", flags=0)
    dialog.set_default_size(320, -1)

    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
    vbox.set_border_width(15)

    label = Gtk.Label(label="Enter password:")
    label.set_xalign(0)

    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char("●")

    show_pw = Gtk.CheckButton(label="Show password")
    show_pw.connect("toggled", lambda cb: entry.set_visibility(cb.get_active()))

    # Warning label (hidden by default)
    warning = Gtk.Label(label="")
    warning.set_xalign(0)
    warning.get_style_context().add_class("error")
    warning.set_no_show_all(True)

    vbox.pack_start(label, False, False, 0)
    vbox.pack_start(entry, False, False, 0)
    vbox.pack_start(show_pw, False, False, 0)
    vbox.pack_start(warning, False, False, 0)

    # Custom buttons
    button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    button_box.set_halign(Gtk.Align.CENTER)

    btn_cancel = Gtk.Button(label="Cancel")
    btn_cancel.connect("clicked", lambda b: dialog.response(Gtk.ResponseType.CANCEL))
    btn_ok = Gtk.Button(label="OK")
    button_box.pack_start(btn_cancel, False, False, 0)
    button_box.pack_start(btn_ok, False, False, 0)

    vbox.pack_start(button_box, False, False, 0)
    dialog.get_content_area().add(vbox)

    # Function to attempt connection
    def try_connect(_btn=None):
        password = entry.get_text()
        try:
            child = pexpect.spawn("snx", encoding="utf-8", timeout=10)

            idx = child.expect(["[Pp]assword:", "SNX: Access denied", pexpect.EOF, pexpect.TIMEOUT])

            if idx == 0:  # got password prompt
                child.sendline(password)
                idx2 = child.expect(
                    ["SNX: Access denied", pexpect.TIMEOUT, pexpect.EOF],
                    timeout=5
                )
                if idx2 == 0:
                    warning.set_text("Wrong password, please try again")
                    warning.show()
                    entry.set_text("")
                    # Shake the dialog
                    w, h = dialog.get_size()
                    dialog.resize(w+1, h)
                    dialog.resize(w, h)
                    child.close(force=True)
                    return
                else:
                    # Assume success and leave snx running
                    dialog.response(Gtk.ResponseType.OK)

            elif idx == 1:  # immediate denial
                warning.set_text("Wrong password, please try again")
                warning.show()
                entry.set_text("")
                child.close(force=True)
                return
            else:
                warning.set_text("Error: could not connect")
                warning.show()
                child.close(force=True)
                return

        except Exception as e:
            warning.set_text(f"Error: {e}")
            warning.show()

    # Button + Enter bindings
    btn_ok.connect("clicked", try_connect)
    entry.connect("activate", try_connect)

    # Clear warning when user types again
    def on_key(_entry, _event):
        if warning.get_visible():
            warning.hide()
    entry.connect("key-press-event", on_key)

    dialog.show_all()
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        pass
    dialog.destroy()

def on_disconnect(_):
    run_command(["snx", "-d"])

def quit(_=None):
    Gtk.main_quit()

# --- Indicator setup ---
indicator = AppIndicator3.Indicator.new(
    APP_ID,
    "network-vpn-symbolic",
    AppIndicator3.IndicatorCategory.APPLICATION_STATUS
)
indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

menu = Gtk.Menu()
item_connect = Gtk.MenuItem.new_with_label("Connect")
item_connect.connect("activate", on_connect)

item_disconnect = Gtk.MenuItem.new_with_label("Disconnect")
item_disconnect.connect("activate", on_disconnect)

menu.append(Gtk.SeparatorMenuItem())

item_quit = Gtk.MenuItem.new_with_label("Quit")
item_quit.connect("activate", quit)
menu.append(item_quit)

menu.show_all()
indicator.set_menu(menu)

Notify.init(APP_ID)

# --- Status check loop ---
def check_process():
    global last_status
    connected = False

    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "dev", "show", "tunsnx"],
            stderr=subprocess.DEVNULL,
            text=True
        )
        if out.strip():
            connected = True
    except subprocess.CalledProcessError:
        connected = False

    # Update icon + tooltip
    if connected:
        indicator.set_icon("network-vpn-symbolic")
        indicator.set_title("SNX Connected")

        if last_status is not True:
            Notify.Notification.new("SNX Status", "Connected", "network-vpn-symbolic").show()

        # Ensure only "Disconnect" is in menu
        if item_disconnect not in menu.get_children():
            menu.insert(item_disconnect, 0)
        if item_connect in menu.get_children():
            menu.remove(item_connect)

    else:
        indicator.set_icon("network-vpn-disconnected-symbolic")
        indicator.set_title("SNX Disconnected")

        if last_status is not False:
            Notify.Notification.new("SNX Status", "Disconnected", "network-vpn-disconnected-symbolic").show()

        # Ensure only "Connect" is in menu
        if item_connect not in menu.get_children():
            menu.insert(item_connect, 0)
        if item_disconnect in menu.get_children():
            menu.remove(item_disconnect)

    menu.show_all()
    last_status = connected
    return True

GLib.timeout_add_seconds(3, check_process)
check_process()

signal.signal(signal.SIGINT, signal.SIG_DFL)
Gtk.main()

