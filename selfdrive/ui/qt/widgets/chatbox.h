#pragma once

#include <QLabel>
#include <QStackedWidget>
#include <QVBoxLayout>
#include <QWidget>

#include "selfdrive/ui/qt/widgets/input.h"

// widget for paired users without prime
class ChatboxWidget : public QFrame {
  Q_OBJECT
public:
  explicit ChatboxWidget(QWidget* parent = 0);
};
