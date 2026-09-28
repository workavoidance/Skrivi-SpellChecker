"""Native UI integration checks with an authored sentence, no private corpus."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QPushButton,QTabWidget
from PySide6.QtTest import QTest
from main import Rett,application_stylesheet
app=QApplication([]);app.setStyleSheet(application_stylesheet(app.palette()));window=Rett();window.show()
text='Jeg skrev en meldnig til læreren i går.'
window.editor.setPlainText(text);QTest.mouseClick(window.check_button,Qt.MouseButton.LeftButton)
started=time.monotonic()
while window.busy and time.monotonic()-started<150:app.processEvents();QTest.qWait(50)
assert window.review,window.status.text()
token=next(t for t in window.review.pending() if t['word']=='meldnig');window.selected=token['id'];window.refresh();app.processEvents()
assert 'melding' in token['suggestions'];assert window.entries['melding']['senses']
window.grab().save(str(ROOT/'results/rett-review-wide.png'))
# Verify exact replacement and undo through real UI controls.
choose=next(b for b in window.side.findChildren(QPushButton) if b.text()=='Velg melding');QTest.mouseClick(choose,Qt.MouseButton.LeftButton)
assert window.text()=='Jeg skrev en melding til læreren i går.'
QTest.mouseClick(window.undo_button,Qt.MouseButton.LeftButton);assert window.text()==text
window.resize(700,850);QTest.qWait(150);assert window.splitter.orientation()==Qt.Orientation.Vertical
window.grab().save(str(ROOT/'results/rett-review-narrow.png'))
# Access to candidates below first three.
window.resize(1120,800);token=next(t for t in window.review.pending() if t['word']=='meldnig')
token['more']=['meldinger'];window.selected=token['id'];window.refresh();app.processEvents()
more=next(b for b in window.side.findChildren(QPushButton) if b.text().startswith('Flere forslag'))
QTest.mouseClick(more,Qt.MouseButton.LeftButton);app.processEvents()
extra=next(b for b in window.side.findChildren(QPushButton) if b.text()=='Velg meldinger');assert extra.isVisible()
QTest.mouseClick(extra,Qt.MouseButton.LeftButton);assert 'meldinger' in window.text();window.undo()
# Settings use the same family tab ordering.
def inspect_settings():
    dialog=app.activeModalWidget();tabs=dialog.findChild(QTabWidget)
    assert [tabs.tabText(i) for i in range(tabs.count())]==['Generelt','Snarveier','Modeller','Personvern','Om']
    dialog.grab().save(str(ROOT/'results/rett-settings.png'));dialog.accept()
QTimer.singleShot(200,inspect_settings);window.settings()
window.saved_text=window.text();window.close();app.processEvents()
print(json.dumps({'real_check':True,'replacement_undo':True,'more_suggestions':True,'responsive_layout':True,'settings_tabs':True,'seconds':round(time.monotonic()-started,2)}))
