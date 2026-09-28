"""Skrivi Rett — native, local Norwegian spelling review."""
import json,os,sys
from pathlib import Path
from PySide6.QtCore import Qt,QProcess,QProcessEnvironment,QSettings,QTimer,QUrl
from PySide6.QtGui import QColor,QFont,QIcon,QPainter,QPen,QPixmap,QKeySequence,QShortcut,QDesktopServices
from PySide6.QtWidgets import (QApplication,QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,
 QPushButton,QPlainTextEdit,QTextBrowser,QStackedWidget,QSplitter,QScrollArea,QFrame,
 QTabWidget,QSpinBox,QCheckBox,QFormLayout,QFileDialog,QMessageBox,QProgressBar)
from theme import application_stylesheet
from review import Review

VERSION='0.1.0'
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
CACHE=Path(os.environ.get('SKRIVI_CACHE_DIR') or Path(os.environ['LOCALAPPDATA'])/'Skrivi')
RUNTIME=CACHE/'runtime/norwegian-py312-v1/Scripts/python.exe'

def label(text,role=None):
    w=QLabel(text);w.setWordWrap(True);w.setTextFormat(Qt.TextFormat.PlainText)
    if role:w.setProperty('uiRole',role)
    return w

def button(text,action,primary=False):
    w=QPushButton(text);w.setAutoDefault(False);w.clicked.connect(action)
    if primary:w.setProperty('buttonRole','primary')
    return w

def icon():
    result=QIcon()
    for size in (16,32,48,64,128,256):
        pix=QPixmap(size,size);pix.fill(Qt.GlobalColor.transparent)
        p=QPainter(pix);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.scale(size/100,size/100)
        pen=QPen(QColor('#F05A24'),9);pen.setCapStyle(Qt.PenCapStyle.RoundCap);pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen);p.drawLine(19,52,40,73);p.drawLine(40,73,82,24);p.end();result.addPixmap(pix)
    return result

class Rett(QDialog):
    def __init__(self):
        super().__init__();self.setWindowTitle('Skrivi Rett');self.setWindowIcon(icon())
        self.resize(1120,800);self.setMinimumSize(660,570)
        self.prefs=QSettings('Skrivi','Rett');self.review=None;self.selected=None;self.entries={}
        self.busy=False;self.request_id=0;self.buffer=b'';self.saved_text='';self.remembering=None
        self.worker=QProcess(self);self.worker.readyReadStandardOutput.connect(self.receive)
        self.worker.readyReadStandardError.connect(lambda:self.worker.readAllStandardError())
        self.worker.errorOccurred.connect(self.worker_error);self.worker.finished.connect(self.worker_finished)
        self.speech=QProcess(self);self.speech.finished.connect(self.speech_finished)
        self.speech.errorOccurred.connect(lambda _:self.status.setText('Opplesning kunne ikke startes.'))
        self.timeout=QTimer(self);self.timeout.setSingleShot(True);self.timeout.setInterval(180000)
        self.timeout.timeout.connect(self.timed_out)
        root=QVBoxLayout(self);root.setContentsMargins(24,22,24,18);root.setSpacing(12)
        header=QHBoxLayout();head=QVBoxLayout();head.addWidget(label('Skrivi Rett','eyebrow'))
        head.addWidget(label('Skriv fritt. Sjekk etterpå.','windowTitle'))
        head.addWidget(label('Norsk bokmål · Alt behandles på denne PC-en.','secondary'));header.addLayout(head,1)
        mark=QLabel();mark.setPixmap(self.windowIcon().pixmap(44,44));header.addWidget(mark);root.addLayout(header)
        self.splitter=QSplitter(Qt.Orientation.Horizontal);root.addWidget(self.splitter,1)
        writing=QWidget();left=QVBoxLayout(writing);left.setContentsMargins(0,0,8,0)
        toolbar=QHBoxLayout();toolbar.addWidget(button('Lim inn',self.paste));toolbar.addWidget(button('Åpne…',self.open_file))
        toolbar.addStretch();self.count=label('0 ord','secondary');toolbar.addWidget(self.count);left.addLayout(toolbar)
        self.stack=QStackedWidget();self.editor=QPlainTextEdit();self.editor.setPlaceholderText('Skriv eller lim inn teksten din her. Du får ingen rettelser før du velger Sjekk teksten.')
        self.editor.setAccessibleName('Tekst som skal sjekkes');self.editor.textChanged.connect(self.update_count)
        self.browser=QTextBrowser();self.browser.setOpenLinks(False);self.browser.anchorClicked.connect(self.word_clicked)
        self.browser.setAccessibleName('Sjekket tekst. Velg et markert ord for å se forslag.')
        self.stack.addWidget(self.editor);self.stack.addWidget(self.browser);left.addWidget(self.stack,1)
        self.legend=label('Grønn: ingen feil funnet · Oransje: usikkert · Rød: mulig feil','secondary');left.addWidget(self.legend)
        row=QHBoxLayout();self.check_button=button('Sjekk teksten',self.check,True);row.addWidget(self.check_button)
        self.cancel_button=button('Avbryt sjekk',self.cancel_check);row.addWidget(self.cancel_button);self.cancel_button.hide()
        self.edit_button=button('Skriv videre',self.edit);row.addWidget(self.edit_button)
        self.undo_button=button('Angre retting',self.undo);row.addWidget(self.undo_button);left.addLayout(row)
        output=QHBoxLayout();output.addWidget(button('Kopier teksten',self.copy));output.addWidget(button('Lagre tekst…',self.save_file));output.addStretch();left.addLayout(output)
        self.splitter.addWidget(writing)
        self.side=QScrollArea();self.side.setWidgetResizable(True);self.side.setMinimumWidth(300);self.splitter.addWidget(self.side)
        self.splitter.setSizes([670,380]);self.splitter.setChildrenCollapsible(False)
        root.addWidget(button('Innstillinger',self.settings))
        self.status=label('Klar. Teksten lagres bare hvis du velger Lagre tekst.','secondary');root.addWidget(self.status)
        self.progress=QProgressBar();self.progress.setRange(0,0);self.progress.setTextVisible(False);self.progress.setMaximumHeight(6);root.addWidget(self.progress);self.progress.hide()
        self.edit_button.setEnabled(False);self.undo_button.setEnabled(False)
        for key,action in [('Ctrl+Return',self.check),('Ctrl+S',self.save_file),('Ctrl+O',self.open_file)]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(action)
        self.set_font(int(self.prefs.value('font_size',14)));self.render_side()
        self.adapt_layout()
    def text(self):return self.review.text if self.review else self.editor.toPlainText()
    def update_count(self):self.count.setText(f'{len(self.text().split())} ord')
    def set_font(self,size):
        self.prefs.setValue('font_size',size)
        for w in (self.editor,self.browser):
            f=QFont('Segoe UI',size);w.setFont(f);w.document().setDefaultFont(f)
    def adapt_layout(self):
        horizontal=self.width()>=960
        self.splitter.setOrientation(Qt.Orientation.Horizontal if horizontal else Qt.Orientation.Vertical)
        self.side.setMinimumHeight(180 if not horizontal else 0)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'splitter'):self.adapt_layout()
    def ensure_worker(self):
        if not RUNTIME.is_file():raise RuntimeError('Den lokale språkmotoren mangler. Denne første prøveversjonen bruker cachen fra sandkassen. Se Innstillinger → Modeller.')
        if self.worker.state()==QProcess.ProcessState.NotRunning:
            env=QProcessEnvironment.systemEnvironment();env.remove('PYTHONPATH');env.remove('PYTHONHOME');env.insert('PYTHONUTF8','1');env.insert('PYTHONIOENCODING','utf-8')
            self.worker.setProcessEnvironment(env);self.worker.start(str(RUNTIME),['-u',str(ROOT/'desktop/worker.py')])
            if not self.worker.waitForStarted(3000):raise RuntimeError('Språkmotoren kunne ikke startes.')
    def send(self,payload):
        self.ensure_worker();self.request_id+=1;payload['id']=self.request_id
        self.worker.write((json.dumps(payload,ensure_ascii=False)+'\n').encode('utf-8'));self.timeout.start()
    def set_busy(self,busy):
        self.busy=busy;self.check_button.setEnabled(not busy);self.editor.setReadOnly(busy);self.cancel_button.setVisible(busy)
        self.edit_button.setEnabled(not busy and self.review is not None)
        self.undo_button.setEnabled(not busy and bool(self.review and self.review.history))
        self.side.setEnabled(not busy);self.progress.setVisible(busy)
    def check(self):
        if self.busy:return
        text=self.text()
        if not text.strip():self.status.setText('Skriv eller lim inn litt tekst først.');return
        self.pending_text=text;self.set_busy(True);self.status.setText('Sjekker teksten lokalt. Første sjekk kan ta litt ekstra tid…')
        try:self.send({'action':'check','text':text})
        except Exception as exc:self.set_busy(False);self.status.setText(str(exc))
    def receive(self):
        self.buffer+=bytes(self.worker.readAllStandardOutput())
        while b'\n' in self.buffer:
            line,self.buffer=self.buffer.split(b'\n',1)
            try:data=json.loads(line)
            except (ValueError,UnicodeError):continue
            if data.get('id')!=self.request_id:continue
            self.timeout.stop();self.set_busy(False)
            if not data.get('ok'):
                self.remembering=None;self.status.setText('Sjekken kunne ikke fullføres: '+data.get('error','Ukjent feil'));continue
            if data.get('remembered'):
                if self.review and self.remembering is not None:self.review.decide(self.remembering)
                self.remembering=None
            else:
                self.review=Review(self.pending_text,data['result']);self.entries=data['help'];self.stack.setCurrentWidget(self.browser)
            self.selected=None;self.refresh()
    def worker_error(self,_):
        if self.busy:self.timeout.stop();self.set_busy(False);self.status.setText('Språkmotoren kunne ikke startes. Se Innstillinger → Modeller.')
    def worker_finished(self,*_):
        self.buffer=b''
        if self.busy:self.timeout.stop();self.set_busy(False);self.status.setText('Språkmotoren stoppet. Teksten er bevart; prøv Sjekk teksten på nytt.')
    def cancel_check(self):
        self.timeout.stop();self.set_busy(False);self.request_id+=1;self.worker.kill();self.status.setText('Sjekken er avbrutt. Teksten er bevart.')
    def timed_out(self):
        self.set_busy(False);self.worker.kill();self.status.setText('Sjekken tok for lang tid. Teksten er bevart. Prøv et kortere avsnitt.')
    def refresh(self):
        if not self.review:return
        pending=self.review.pending()
        if self.selected not in [t['id'] for t in pending]:self.selected=pending[0]['id'] if pending else None
        self.browser.setHtml(self.review.markup(self.selected));self.update_count();self.set_busy(False);self.render_side()
        self.status.setText(f'{len(pending)} ord å vurdere. Du velger selv hva som skal endres.' if pending else 'Gjennomgangen er ferdig. Du kan kopiere teksten eller skrive videre.')
    def word_clicked(self,url):
        if self.busy:return
        if url.scheme()=='word':self.selected=int(url.path());self.refresh()
    def render_side(self):
        page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(14,12,14,12);layout.setSpacing(12)
        old=self.side.takeWidget()
        if old:old.deleteLater()
        self.side.setWidget(page)
        if self.selected is None or not self.review:
            layout.addWidget(label('Dine ord. Dine valg.','pageTitle'))
            layout.addWidget(label('Skriv ferdig tanken først. Når du sjekker teksten, vises forslag med forklaringer og eksempler her.'))
            layout.addWidget(label('Ingenting blir skrevet om automatisk.','secondary'));layout.addStretch();return
        token=next(t for t in self.review.tokens if t['id']==self.selected)
        layout.addWidget(label(token['word'],'pageTitle'))
        layout.addWidget(label('Mulig stavefeil' if token['status']=='LIKELY_ERROR' else 'Usikkert ord – vurder forslagene','secondary'))
        actions=QHBoxLayout();actions.addWidget(button('Behold',lambda:self.decide(None)))
        actions.addWidget(button('Husk ordet',lambda:self.remember(token)));layout.addLayout(actions)
        nav=QHBoxLayout();nav.addWidget(button('Forrige',lambda:self.navigate(-1)));nav.addWidget(button('Neste',lambda:self.navigate(1)));layout.addLayout(nav)
        for suggestion in token['suggestions']:self.candidate(layout,token,suggestion)
        if token.get('more'):
            extra=QWidget();box=QVBoxLayout(extra);box.setContentsMargins(0,0,0,0);extra.hide()
            toggle=button(f'Flere forslag ({len(token["more"])})',lambda:extra.setVisible(not extra.isVisible()));layout.addWidget(toggle)
            for suggestion in token['more']:self.candidate(box,token,suggestion)
            layout.addWidget(extra)
        if not token['suggestions']:layout.addWidget(label('Ingen sikre forslag. Du kan beholde ordet eller skrive videre og endre det selv.'))
        layout.addStretch()
    def candidate(self,layout,token,word):
        frame=QFrame();frame.setProperty('uiRole','card');box=QVBoxLayout(frame);box.setContentsMargins(14,12,14,12)
        box.addWidget(label(word,'sectionTitle'));entry=self.entries.get(word);senses=(entry or {}).get('senses',[])
        if senses:
            box.addWidget(label('En mulig betydning','secondary'))
            self.sense(box,word,senses[0])
            if len(senses)>1:
                other=QWidget();otherbox=QVBoxLayout(other);otherbox.setContentsMargins(0,0,0,0);other.hide()
                for sense in senses[1:]:self.sense(otherbox,word,sense)
                box.addWidget(button('Andre betydninger',lambda:other.setVisible(not other.isVisible())));box.addWidget(other)
            box.addWidget(label('Bokmålsordboka · UiB og Språkrådet. Betydningen er ikke valgt ut fra setningen.','secondary'))
        else:box.addWidget(label('Ingen forklaring tilgjengelig for dette ordet.','secondary'))
        row=QHBoxLayout();row.addWidget(button('Velg '+word,lambda:self.decide(word),True));row.addWidget(button('Hør ordet',lambda:self.speak(word)));box.addLayout(row);layout.addWidget(frame)
    def sense(self,box,word,sense):
        definition=sense.get('definition','');box.addWidget(label(definition))
        examples=sense.get('examples',[])
        if examples:box.addWidget(label('Eksempel: '+examples[0]['text']))
        spoken=(examples[0]['text'] if examples else definition)
        box.addWidget(button('Hør forklaringen',lambda:self.speak(word+'. '+spoken)))
    def navigate(self,step):
        ids=[t['id'] for t in self.review.pending()]
        if ids:self.selected=ids[(ids.index(self.selected)+step)%len(ids)];self.refresh()
    def decide(self,replacement):
        if self.busy:return
        try:self.review.decide(self.selected,replacement);self.selected=None;self.refresh()
        except ValueError as exc:self.status.setText(str(exc))
    def remember(self,token):
        self.remembering=token['id'];self.set_busy(True)
        try:self.send({'action':'remember','word':token['word']})
        except Exception as exc:self.remembering=None;self.set_busy(False);self.status.setText(str(exc))
    def undo(self):
        if not self.busy and self.review:self.review.undo();self.selected=None;self.refresh()
    def edit(self):
        if self.busy:return
        value=self.text();self.review=None;self.selected=None;self.entries={};self.editor.setPlainText(value)
        self.stack.setCurrentWidget(self.editor);self.set_busy(False);self.render_side();self.editor.setFocus()
    def replace_text(self,value):
        if self.busy:return
        if self.text().strip() and QMessageBox.question(self,'Erstatt teksten?','Vil du erstatte teksten i vinduet?')!=QMessageBox.StandardButton.Yes:return
        self.edit();self.editor.setPlainText(value)
    def paste(self):self.replace_text(QApplication.clipboard().text())
    def copy(self):QApplication.clipboard().setText(self.text());self.status.setText('Teksten er kopiert.')
    def open_file(self):
        if self.busy:return
        path,_=QFileDialog.getOpenFileName(self,'Åpne tekst','','Tekstfiler (*.txt)')
        if path:
            try:
                value=Path(path).read_text(encoding='utf-8-sig');self.replace_text(value)
            except (OSError,UnicodeError):QMessageBox.warning(self,'Kan ikke åpne','Velg en tekstfil lagret som UTF-8.')
    def save_file(self):
        path,_=QFileDialog.getSaveFileName(self,'Lagre tekst','Tekst.txt','Tekstfiler (*.txt)')
        if path:
            try:Path(path).write_text(self.text(),encoding='utf-8');self.saved_text=self.text();self.status.setText('Teksten er lagret.')
            except OSError:QMessageBox.warning(self,'Kan ikke lagre','Velg en mappe du har tilgang til.')
    def speak(self,text):
        if self.speech.state()!=QProcess.ProcessState.NotRunning:self.speech.kill();self.speech.waitForFinished(1500)
        if not RUNTIME.is_file():self.status.setText('Den lokale språkmotoren mangler.');return
        env=QProcessEnvironment.systemEnvironment();env.remove('PYTHONPATH');env.remove('PYTHONHOME');env.insert('PYTHONUTF8','1');self.speech.setProcessEnvironment(env)
        self.speech.start(str(RUNTIME),[str(ROOT/'desktop/worker.py'),'--speech'])
        if self.speech.waitForStarted(2000):self.speech.write((json.dumps({'text':text[:600]},ensure_ascii=False)+'\n').encode());self.speech.closeWriteChannel();self.status.setText('Leser med Windows-stemmen…')
    def speech_finished(self,code,*_):
        self.speech.readAllStandardError()
        self.status.setText('Opplesning ferdig.' if code==0 else 'Opplesning er ikke tilgjengelig. Kontroller at en norsk Windows-stemme er installert.')
    def settings(self):
        dialog=QDialog(self);dialog.setWindowTitle('Skrivi Rett · Innstillinger');dialog.resize(760,660)
        root=QVBoxLayout(dialog);root.setContentsMargins(24,22,24,18)
        root.addWidget(label('Skrivi Rett','eyebrow'));root.addWidget(label('Innstillinger','windowTitle'))
        tabs=QTabWidget();root.addWidget(tabs,1);pages=[]
        for name in ('Generelt','Snarveier','Modeller','Personvern','Om'):
            page=QWidget();page.setObjectName('settingsPage');box=QVBoxLayout(page);box.setSpacing(14)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page);tabs.addTab(scroll,name);pages.append(box)
        general,shortcuts,models,privacy,about=pages
        general.addWidget(label('Skriving og lesing','pageTitle'));general.addWidget(label('Språk: Norsk bokmål. Sjekkingen starter bare når du ber om det.'))
        size=QSpinBox();size.setRange(11,26);size.setValue(self.editor.font().pointSize());size.valueChanged.connect(self.set_font)
        form=QFormLayout();form.addRow('Tekststørrelse',size);general.addLayout(form)
        general.addWidget(label('Utseendet følger Windows, med samme farger og innstillinger som Skrivi Snakk og Lytt.'))
        shortcuts.addWidget(label('Snarveier i Skrivi Rett','pageTitle'));shortcuts.addWidget(label('Ctrl+Enter: Sjekk teksten\nCtrl+S: Lagre tekst\nCtrl+O: Åpne tekst\nCtrl+C / Ctrl+V: Kopier og lim inn i skrivefeltet\nTab: Flytt mellom knapper og forslag'))
        models.addWidget(label('Norsk språkstøtte','pageTitle'))
        for name,path in [('Språkmotor',RUNTIME),('Ordforklaringer',CACHE/'lexical/bokmaal/dictionary.sqlite3'),('Ordformer',CACHE/'lexical/ordbank-20220201/ordbank.sqlite3'),('Grunnformer',CACHE/'lexical/ordbank-20220201/help-baseforms.sqlite3')]:
            models.addWidget(label(name+(': Tilgjengelig' if path.is_file() else ': Mangler')))
        models.addWidget(label('Nuspell og NorBERT3 Small brukes til stavekontroll og kontekst. Denne lokale prøveversjonen gjenbruker språkressursene fra sandkassen. Ingenting lastes ned automatisk.'))
        models.addWidget(label(str(CACHE),'secondary'));models.addWidget(button('Åpne ressursmappen',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(CACHE)))))
        privacy.addWidget(label('Teksten blir på PC-en','pageTitle'));privacy.addWidget(label('Ingen skytjeneste, telemetri eller automatisk teksthistorikk. Teksten finnes i minnet til du lukker vinduet. Lagre tekst skriver bare til filen du velger. Kopier legger teksten på Windows-utklippstavlen.'))
        privacy.addWidget(label('Husk ordet lagrer bare det valgte ordet i din lokale ordliste. Innstillinger og språkressurser bevares når appen oppdateres eller avinstalleres.'))
        about.addWidget(label('Skrivi Rett '+VERSION,'pageTitle'));about.addWidget(label('Lokal prøveversjon · Norsk bokmål\nSkriv fritt. Sjekk etterpå. Velg dine egne rettelser.'))
        about.addWidget(label('Programkode: MIT. Grensesnittet bygger på Skrivi Lytt og Snakk. Qt/PySide6: LGPLv3. Språkressurser har egne lisenser.'))
        about.addWidget(label('Ordforklaringer: Bokmålsordboka, Universitetet i Bergen og Språkrådet. Ordbokdata brukes fra eksisterende lokal testcache; avklaring av distribusjonsvilkår gjenstår før offentlig utgivelse.'))
        about.addWidget(button('Prosjekt på GitHub',lambda:QDesktopServices.openUrl(QUrl('https://github.com/workavoidance/Skrivi-SpellChecker'))))
        for page in pages:page.addStretch()
        root.addWidget(button('Lukk',dialog.accept));dialog.exec()
    def closeEvent(self,event):
        if self.text().strip() and self.text()!=self.saved_text:
            answer=QMessageBox.question(self,'Lukk Skrivi Rett?','Teksten er ikke lagret i en fil. Vil du lukke likevel?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:event.ignore();return
        self.timeout.stop();self.worker.kill();self.speech.kill();self.worker.waitForFinished(2000);self.speech.waitForFinished(2000);event.accept()

def main():
    app=QApplication(sys.argv);app.setApplicationName('Skrivi Rett');app.setApplicationVersion(VERSION)
    app.setStyleSheet(application_stylesheet(app.palette()));window=Rett()
    if '--check-startup' in sys.argv:
        assert window.windowTitle()=='Skrivi Rett';return 0
    window.show()
    if '--self-test' in sys.argv:
        output=Path(sys.argv[sys.argv.index('--self-test')+1])
        sample='Jeg skrev en meldnig til læreren i går.'
        window.editor.setPlainText(sample);window.check()
        checks=QTimer(window);checks.setInterval(100)
        def finish_check():
            if window.busy:return
            checks.stop()
            try:
                assert window.review,window.status.text()
                token=next(t for t in window.review.pending() if t['word']=='meldnig')
                assert 'melding' in token['suggestions']
                assert window.entries['melding']['senses']
                window.selected=token['id'];window.decide('melding')
                assert window.text()=='Jeg skrev en melding til læreren i går.'
                window.undo();assert window.text()==sample
                result={'ok':True,'cached_model':True,'definition':True,'exact_replacement_and_undo':True}
                code=0
            except Exception as exc:result={'ok':False,'error':str(exc)};code=1
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            window.saved_text=window.text();window.close();app.exit(code)
        checks.timeout.connect(finish_check);checks.start()
    if '--screenshot'  in sys.argv:
        output=sys.argv[sys.argv.index('--screenshot')+1]
        def capture():window.grab().save(output);app.quit()
        QTimer.singleShot(700,capture)
    return app.exec()
if __name__=='__main__':sys.exit(main())
