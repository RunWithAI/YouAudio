# Use C++11 standard
CONFIG += c++11

# Console application (not a GUI app with a window)
CONFIG -= app_bundle

# Sources
SOURCES += \
    main.cpp

# Translations
TRANSLATIONS += \
    translations/YouAudioTray_zh_CN.ts

RESOURCES += resources.qrc

# Include required Qt modules
QT += core gui widgets network

# Default rules for deployment
qnx: target.path = /tmp/$${TARGET}/bin
else: unix:!android: target.path = /opt/$${TARGET}/bin
!isEmpty(target.path): INSTALLS += target

