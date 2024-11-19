#include "selfdrive/ui/qt/widgets/chatbox.h"

#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QPushButton>
#include <QStackedWidget>
#include <QTimer>
#include <QVBoxLayout>

#include "selfdrive/ui/qt/util.h"
#include "selfdrive/ui/qt/qt_window.h"

ChatboxWidget::ChatboxWidget(QWidget* parent) : QFrame(parent) {
  QVBoxLayout *main_layout = new QVBoxLayout(this);
  main_layout->setContentsMargins(50, 50, 50, 50);
  main_layout->setSpacing(0);

  QLabel *user_input = new QLabel("User: I want to wash my car ");
  user_input->setStyleSheet("font-size: 36px; font-weight: light; color: white;");
  user_input->setWordWrap(true);
  main_layout->addWidget(user_input, 0, Qt::AlignTop);

  main_layout->addSpacing(30);

  QLabel *agent_response = new QLabel("Agent: From Center for Urban Transportation Research, there's few car wash near you:...");
  agent_response->setStyleSheet("font-size: 36px; font-weight: light; color: white;");
  agent_response->setWordWrap(true);
  main_layout->addWidget(agent_response, 0, Qt::AlignTop);

  main_layout->addStretch();

setStyleSheet(R"(
    ChatboxWidget {
      border-radius: 10px;
      background-color: #333333;
    }
  )");
}