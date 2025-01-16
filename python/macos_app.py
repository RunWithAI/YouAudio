import objc
from Foundation import *
from AppKit import *
import webbrowser
import os
import signal
import sys

class YouAudioDelegate(NSObject):
    statusbar = objc.ivar()
    statusitem = objc.ivar()
    status_menu = objc.ivar()
    dock_menu = objc.ivar()
    host_port = objc.ivar()
    
    def init(self, host_port = 9527):
        self = objc.super(YouAudioDelegate, self).init()
        if self is None: return None        
        # Initialize instance variables
        self.statusbar = None
        self.statusitem = None
        self.status_menu = None
        self.dock_menu = None
        self.host_port = host_port
        return self

    # def setHostPort(self, port):
    #     self.host_port = port

    # Define the action methods with the correct decorator and signature
    @objc.IBAction
    def openWebApp_(self, sender):
        webbrowser.open(f"http://127.0.0.1:{self.host_port}/")
    
    @objc.IBAction
    def quitApp_(self, sender):
        NSApp.terminate_(sender)
    
    def applicationDidFinishLaunching_(self, notification):
        # Set up status bar first
        # self.setup_status_bar()        
        # Set up the dock menu
        self.setup_dock_menu()
        
        # Set the activation policy to regular to show in dock
        NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    
    def setup_dock_menu(self):
        # Create the dock menu
        self.dock_menu = NSMenu.alloc().init()
        
        # Create menu items with explicit selectors
        open_selector = objc.selector(self.openWebApp_, signature=b'v@:@')
        quit_selector = objc.selector(self.quitApp_, signature=b'v@:@')
        
        # Add menu items
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open YouAudio", open_selector, "")
        open_item.setTarget_(self)
        
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", quit_selector, "")
        quit_item.setTarget_(self)
        
        self.dock_menu.addItem_(open_item)
        # self.dock_menu.addItem_(NSMenuItem.separatorItem())
        # self.dock_menu.addItem_(quit_item)
        
        # Set the dock menu
        NSApp.setDockMenu_(self.dock_menu)
    
    def setup_status_bar(self):
        # Create the status bar item
        self.statusbar = NSStatusBar.systemStatusBar()
        self.statusitem = self.statusbar.statusItemWithLength_(22.0)
        
        # Set the status bar icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               "static", "image", "icon.png")
        if os.path.exists(icon_path):
            icon = NSImage.alloc().initWithContentsOfFile_(icon_path)
            icon.setSize_(NSMakeSize(18, 18))
            icon.setTemplate_(True)
            self.statusitem.button().setImage_(icon)
        
        # Create the status bar menu
        self.status_menu = NSMenu.alloc().init()
        
        # Create menu items with explicit selectors
        open_selector = objc.selector(self.openWebApp_, signature=b'v@:@')
        quit_selector = objc.selector(self.quitApp_, signature=b'v@:@')
        
        # Add menu items
        open_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Open YouAudio", open_selector, "")
        open_item.setTarget_(self)
        
        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit", quit_selector, "")
        quit_item.setTarget_(self)
        
        self.status_menu.addItem_(open_item)
        self.status_menu.addItem_(NSMenuItem.separatorItem())
        self.status_menu.addItem_(quit_item)
        
        # Set the menu
        self.statusitem.setMenu_(self.status_menu)

def run_macos_app():
    # Create and set up the application
    app = NSApplication.sharedApplication()
    
    # Create and set up the delegate
    delegate = YouAudioDelegate.alloc().init()
    app.setDelegate_(delegate)
    
    # Bring app to front
    NSApp.activateIgnoringOtherApps_(True)
    
    # Start the application
    app.run()
