/*
 * Teufel IR Serial Bridge + LED-Matrix (Arduino UNO R4 WiFi)
 * ----------------------------------------------------------------------------
 * Serielles Protokoll (115200, eine Zeile):
 *   <HEX>   z.B. 48   -> IR-Befehl  sendNEC(0x5780, 0x48)
 *   m<n>    m0..m7    -> Modus: 0=aus 1=Pegel 2=BPM 3=Smiley 4=VU 5=Herz 6=Spektrum 7=Welle
 *   v<int>  z.B. v126 -> Primaerwert (Pegel 0-100 ODER BPM ; v-1 = Idle "--")
 *   f                 -> Beat (Flash / Puls / Wink)
 *   s<12>             -> Spektrum: 12 Zeichen '0'..'8' = Saeulenhoehen
 * 12x8 monochrom. Die zyklischen Modi animieren selbst (Render-Tick ~22 fps).
 */
#include <IRremote.hpp>
#include "Arduino_LED_Matrix.h"
#include <math.h>

#define IR_SEND_PIN 3
#define TEUFEL_ADDR 0x5780

ArduinoLEDMatrix matrix;

const uint8_t FONT[10][5] = {
  {0b111,0b101,0b101,0b101,0b111},{0b010,0b110,0b010,0b010,0b111},
  {0b111,0b001,0b111,0b100,0b111},{0b111,0b001,0b111,0b001,0b111},
  {0b101,0b101,0b111,0b001,0b001},{0b111,0b100,0b111,0b001,0b111},
  {0b111,0b100,0b111,0b101,0b111},{0b111,0b001,0b010,0b010,0b010},
  {0b111,0b101,0b111,0b101,0b111},{0b111,0b101,0b111,0b001,0b111},
};
// 12-breite Bitmaps (Bit 11 = Spalte 0 / links)
const uint16_t SMILEY[8]   = {0,0,0b000100001000,0,0b001000000100,0b000100001000,0b000011110000,0};
const uint16_t SMILEY_B[8] = {0,0b000100001000,0,0b000111111000,0b001100001100,0b001000000100,0b000111111000,0}; // grosses Grinsen
const uint16_t HEART_S[8]  = {0,0b000011011000,0b000111111100,0b000111111100,0b000011111000,0b000001110000,0b000000100000,0};
const uint16_t HEART_L[8]  = {0b000110011000,0b001111111100,0b011111111110,0b011111111110,0b001111111100,0b000111111000,0b000011110000,0b000001100000};

uint8_t frame[8][12];
int dispMode = 0;
int dispValue = 0;            // -1 = Idle
int spectrum[12];
unsigned long flashUntil = 0; // BPM-Ring
unsigned long beatUntil  = 0; // Smiley/Herz-Puls
unsigned long lastTick   = 0;
unsigned long lastFrameTx = 0;   // throttle for streaming the frame to the bridge
float wavePhase = 0;
int vuPeak = 0;               // Peak-Hold fuer VU

void clearFrame(){ for(int r=0;r<8;r++) for(int c=0;c<12;c++) frame[r][c]=0; }
void px(int x,int y){ if(x>=0&&x<12&&y>=0&&y<8) frame[y][x]=1; }
void drawBitmap(const uint16_t b[8]){ for(int y=0;y<8;y++) for(int x=0;x<12;x++) if(b[y]&(1<<(11-x))) px(x,y); }

void drawDigit(int d,int x,int yTop){ if(d<0||d>9)return; for(int r=0;r<5;r++){uint8_t b=FONT[d][r]; if(b&4)px(x,yTop+r); if(b&2)px(x+1,yTop+r); if(b&1)px(x+2,yTop+r);} }
void drawNumber(int v,int yTop){ if(v<0)v=0; if(v>999)v=999; char s[6]; snprintf(s,sizeof(s),"%d",v); int n=strlen(s),w=n*3+(n-1),x=(12-w)/2; for(int i=0;i<n;i++){drawDigit(s[i]-'0',x,yTop); x+=4;} }
void drawDashes(int yTop){ int y=yTop+2; px(2,y);px(3,y);px(4,y); px(7,y);px(8,y);px(9,y); }
void drawIndicator(){ if(dispMode==1){px(0,0);px(1,0);px(0,1);px(1,1);} else if(dispMode==2){px(11,1);px(10,0);px(9,1);} }
void drawBar(int v){ if(v<0)return; int n=(v*12+50)/100; if(n>12)n=12; if(n<0)n=0; for(int x=0;x<n;x++)px(x,7); }
void drawRing(){ for(int x=0;x<12;x++){px(x,0);px(x,7);} for(int y=0;y<8;y++){px(0,y);px(11,y);} }

void drawVU(int v){           // Pegelblock von unten + Peak-Hold-Linie
  if(v<0)v=0; int h=(v*8+50)/100; if(h>8)h=8;
  if(h>vuPeak) vuPeak=h;
  for(int k=0;k<h;k++) for(int x=1;x<11;x++) px(x,7-k);
  if(vuPeak>0){ int py=7-(vuPeak-1); for(int x=1;x<11;x++) px(x,py); }
}

void drawSpectrum(){ for(int x=0;x<12;x++){ int h=spectrum[x]; if(h>8)h=8; for(int k=0;k<h;k++) px(x,7-k);} }

void drawWelle(){             // selbstlaufende Sinus-Welle (gefuellt)
  for(int x=0;x<12;x++){ int top=(int)lroundf(3.5f+3.0f*sinf(x*0.55f+wavePhase)); if(top<0)top=0; if(top>7)top=7; for(int y=top;y<8;y++) px(x,y); }
}

void updateDisplay(){
  clearFrame();
  bool beat = (millis()<beatUntil);
  switch(dispMode){
    case 1: drawIndicator(); if(dispValue<0)drawDashes(2); else {drawNumber(dispValue,2); drawBar(dispValue);} break;            // Pegel
    case 2: drawIndicator(); if(dispValue<0)drawDashes(3); else drawNumber(dispValue,3); if(millis()<flashUntil)drawRing(); break; // BPM
    case 3: drawBitmap(beat?SMILEY_B:SMILEY); break;                                                                                // Smiley
    case 4: drawVU(dispValue<0?0:dispValue); break;                                                                                // VU
    case 5: drawBitmap(beat?HEART_L:HEART_S); break;                                                                               // Herz
    case 6: drawSpectrum(); break;                                                                                                  // Spektrum
    case 7: drawWelle(); break;                                                                                                     // Welle
    default: break;                                                                                                                 // aus
  }
  matrix.renderBitmap(frame,8,12);
  // stream the ACTUAL 12x8 frame back to the bridge (<=22fps) for the 1:1 web
  // viewer: 'F' + 8 rows * 3 hex (each row = 12 bits, col0 = MSB).
  if(millis()-lastFrameTx >= 45){
    lastFrameTx = millis();
    char fb[26]; fb[0]='F';
    for(int r=0;r<8;r++){ int v=0; for(int c=0;c<12;c++) if(frame[r][c]) v|=(1<<(11-c)); sprintf(fb+1+r*3,"%03X",v); }
    Serial.println(fb);
  }
}

void setup(){
  Serial.begin(115200);
  IrSender.begin(IR_SEND_PIN);
  matrix.begin();
  clearFrame(); matrix.renderBitmap(frame,8,12);
  Serial.println(F("Teufel IR + Matrix bereit (NEC 0x5780)"));
}

String buf;
void loop(){
  // --- Animations-Tick (~22 fps) fuer selbstlaufende/abklingende Modi ---
  unsigned long now=millis();
  if(now-lastTick>=45){
    lastTick=now;
    wavePhase+=0.18f;
    if(vuPeak>0 && (now/120)%2==0) {} // Peak haelt; faellt unten
    static unsigned long peakTick=0; if(now-peakTick>200){peakTick=now; if(vuPeak>0)vuPeak--;}
    if(dispMode>=3 || (dispMode==2 && now<flashUntil)) updateDisplay();
  }
  // --- Serielle Befehle ---
  while(Serial.available()){
    char c=Serial.read();
    if(c==13||c==10){
      buf.trim();
      if(buf.length()>0){
        char k=buf.charAt(0);
        if(k=='m'){ dispMode=buf.substring(1).toInt(); vuPeak=0; updateDisplay(); Serial.print(F("M"));Serial.println(dispMode); }
        else if(k=='v'){ dispValue=buf.substring(1).toInt(); updateDisplay(); }
        else if(k=='f'){ flashUntil=now+90; beatUntil=now+160; updateDisplay(); }
        else if(k=='s'){ String d=buf.substring(1); for(int i=0;i<12;i++){ char ch=(i<(int)d.length())?d.charAt(i):'0'; int h=ch-'0'; if(h<0)h=0; if(h>8)h=8; spectrum[i]=h; } updateDisplay(); }
        else { long val=strtol(buf.c_str(),NULL,16); IrSender.sendNEC(TEUFEL_ADDR,(uint8_t)val,0); Serial.print(F("TX 0x"));Serial.println((uint8_t)val,HEX); }
      }
      buf="";
    } else if(buf.length()<16){ buf+=c; }
  }
}
