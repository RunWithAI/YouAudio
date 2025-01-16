#include <QApplication>
#include <QSystemTrayIcon>
#include <QMenu>
#include <QAction>
#include <QProcess>
#include <QDesktopServices>
#include <QUrl>
#include <QNetworkAccessManager>
#include <QNetworkRequest>
#include <QNetworkReply>
#include <QTimer>
#include <QFileInfo>
#include <QJsonDocument>
#include <QJsonObject>
#include <QFile>
#include <QInputDialog>
#include <QDir>
#include <QMessageBox>
#include <QThread>
#include <QTimer>
#include <QSharedMemory>
#include <QTranslator>
#include <QLocale>
#include <QObject>

// Helper function to save port to config
bool saveConfiguredPort(const QString& currentDir, int port) {
    QString configDir = currentDir + "/youaudio/_internal";
    QString configPath = configDir + "/config.json";

    // Create directory if it doesn't exist
    QDir dir;
    if (!dir.exists(configDir)) {
        if (!dir.mkpath(configDir)) {
            return false;
        }
    }

    QJsonObject config;

    // Read existing config if it exists
    QFile configFile(configPath);
    if (configFile.open(QIODevice::ReadOnly)) {
        QByteArray configData = configFile.readAll();
        configFile.close();
        QJsonDocument jsonDoc = QJsonDocument::fromJson(configData);
        if (!jsonDoc.isNull() && jsonDoc.isObject()) {
            config = jsonDoc.object();
        }
    }

    // Update port
    config["host_port"] = port;

    // Save config
    QJsonDocument saveDoc(config);
    if (configFile.open(QIODevice::WriteOnly)) {
        configFile.write(saveDoc.toJson());
        configFile.close();
        return true;
    }
    return false;
}

// Helper function to get port from config
int getConfiguredPort(const QString& currentDir) {
    int port = 9527;  // Default port
    
    QString configPath = currentDir + "/youaudio/_internal/config.json";
    QFile configFile(configPath);
    if (configFile.open(QIODevice::ReadOnly)) {
        QByteArray configData = configFile.readAll();
        configFile.close();
        
        QJsonDocument jsonDoc = QJsonDocument::fromJson(configData);
        if (!jsonDoc.isNull() && jsonDoc.isObject()) {
            QJsonObject jsonObj = jsonDoc.object();
            if (jsonObj.contains("host_port")) {
                port = jsonObj["host_port"].toInt();
            }
        }
    }else{
        // If config file doesn't exist, create it
        saveConfiguredPort(currentDir, port);
    }
    return port;
}



bool isYouAudioRunning(quint16 port, int timeout_ms = 3000) {
    QNetworkAccessManager pingManager;
    QNetworkRequest pingRequest(QUrl(QString("http://localhost:%1/api/ping").arg(port)));

    QNetworkReply* reply = pingManager.get(pingRequest);

    QEventLoop loop;
    QObject::connect(reply, &QNetworkReply::finished, &loop, &QEventLoop::quit);

    // Create a timer to enforce the timeout
    QTimer timer;
    timer.setSingleShot(true);
    timer.setInterval(timeout_ms);
    QObject::connect(&timer, &QTimer::timeout, &loop, &QEventLoop::quit);
    timer.start();

    loop.exec();

    bool isRunning = (reply->error() == QNetworkReply::NoError &&
                     reply->attribute(QNetworkRequest::HttpStatusCodeAttribute).toInt() == 200);

    reply->deleteLater();
    return isRunning;
}

// Helper function to start YouAudio
void startYouAudio(const QString& currentDir) {
    QString exePath = currentDir + "/youaudio/youaudio.exe";
    QProcess::startDetached(exePath);
    QThread::msleep(3000);  // Give it a moment to start up
}

int main(int argc, char *argv[]) {
    QApplication a(argc, argv);

    QTranslator translator;
    QString locale = QLocale::system().name();
    if (translator.load(":/translations/YouAudioTray_zh_CN")) {
        a.installTranslator(&translator);
    }else{
        QMessageBox::warning(nullptr, QObject::tr("YouAudio"), QObject::tr("Another instance is already running. 1"));
        return 1;
    }


    // Create shared memory to ensure single instance
    QSharedMemory sharedMemory("YouAudioTrayInstance");
    if (!sharedMemory.create(1)) {
        QMessageBox::warning(nullptr, QObject::tr("YouAudio"), QObject::tr("Another instance is already running."));
        return 1;
    }


    // Create tray icon
    QSystemTrayIcon trayIcon;
    QIcon icon(":/youaudiotray.jpg");
    if (icon.isNull()) {
        qDebug() << "Failed to load tray icon";
    }
    trayIcon.setIcon(icon);
    if (!QSystemTrayIcon::isSystemTrayAvailable()) {
        qDebug() << "System tray is not available";
    }
    trayIcon.setVisible(true);

    // Create the menu for the tray
    QMenu menu;
    QAction *openAction = new QAction(QObject::tr("Open"), &menu);
    QAction *settingsAction = new QAction(QObject::tr("Settings"), &menu);
    QAction *quitAction = new QAction(QObject::tr("Quit"), &menu);

    // Add menu items to the tray menu
    menu.addAction(openAction);
    menu.addAction(settingsAction);
    menu.addSeparator();
    menu.addAction(quitAction);

    // Get current directory once
    QString currentDir = QFileInfo(argv[0]).absolutePath();
    
    // Get configured port
    int port = getConfiguredPort(currentDir);

    // Settings action to configure port
    QObject::connect(settingsAction, &QAction::triggered, [&port, currentDir]() {
        bool ok;
        int newPort = QInputDialog::getInt(nullptr, 
            QObject::tr("Port Configuration"),
            QObject::tr("Enter YouAudio port number:"),
            port,  // current value
            1024,  // min value
            65535, // max value
            1,     // step
            &ok);
        
        if (ok) {
            // Save the new port
            if (saveConfiguredPort(currentDir, newPort)) {
                // Check if YouAudio is running on the old port
                if (isYouAudioRunning(port)) {
                    QMessageBox::information(nullptr, 
                        QObject::tr("Port Changed"),
                        QObject::tr("Port configuration saved. Please restart YouAudio for the changes to take effect."));
                }
                port = newPort;
            } else {
                QMessageBox::warning(nullptr,
                    QObject::tr("Error"),
                    QObject::tr("Failed to save port configuration."));
            }
        }
    });

    // Execute "youaudio.exe" and open the browser when "Open" is clicked
    QObject::connect(openAction, &QAction::triggered, [currentDir, port]() {
        if (!isYouAudioRunning(port)) {
            startYouAudio(currentDir);
        }
        QDesktopServices::openUrl(QUrl(QString("http://localhost:%1").arg(port)));
    });

    // Send request to quit endpoint and quit the tray when "Quit" is clicked
    QObject::connect(quitAction, &QAction::triggered, [port, &a]() {
        QNetworkAccessManager *networkManager = new QNetworkAccessManager();
        QNetworkRequest request(QUrl(QString("http://localhost:%1/api/quit").arg(port)));
        networkManager->get(request);
        QTimer::singleShot(1000, &a, &QApplication::quit);
    });

    // Set the context menu for the tray icon
    trayIcon.setContextMenu(&menu);

    // Check and start YouAudio.exe on program start
    if (!isYouAudioRunning(port)) {
        startYouAudio(currentDir);
    }
    QDesktopServices::openUrl(QUrl(QString("http://localhost:%1").arg(port)));

    // Start the application event loop
    return a.exec();
}
