#pragma once

#include <QLabel>
#include <QPushButton>

#include "common/params.h"

class DashcamModeButton : public QPushButton {
  Q_OBJECT

public:
  explicit DashcamModeButton(QWidget* parent = 0);

signals:
  void toggleDashcam();

private:
  void showEvent(QShowEvent *event) override;

  Params params;
  int img_width = 100;
  int horizontal_padding = 30;
  QLabel *mode_label;
  QLabel *mode_icon;

protected:
  void paintEvent(QPaintEvent *event) override;
};
