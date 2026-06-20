/*
 * Teufel Power HiFi - IR Serial Bridge + LED-Matrix-Anzeige (Arduino UNO R4 WiFi)
 * ----------------------------------------------------------------------------
 * Serielles Protokoll (115200, eine Zeile):
 *   <HEX>   z.B. 48  -> IR-Befehl, sendet NEC(0x5780, 0x48)         (IR-Steuerung)
 *   m<n>    m0/m1/m2 -> Matrix-Modus: 0=aus, 1=dB(Pegel), 2=BPM     (Anzeige)
 *   v<int>  z.B. v126 -> Wert fuer aktuellen Modus auf die Matrix
 * IR-Codes sind reine Hex-Ziffern (0-9A-F); m/v sind keine Hex-Zeichen -> eindeutig.
 * Die 12x8-LED-Matrix zeigt IMMER nur einen Wert + kleinen Modus-Indikator
 * (dB = Block oben links, BPM = Spitze oben rechts).
 */
#include <IRremote.hpp>
#include "Arduino_LED_Matrix.h"

#define IR_SEND_PIN 3
#define TEUFEL_ADDR 0x5780

ArduinoLEDMatrix matrix;

// 3x5-Ziffernfont, 5 Zeilen, untere 3 Bit je Zeile (bit2 = links)
const uint8_t FONT[10][5] = {
  {0b111,0b101,0b101,0b101,0b111}, // 0
  {0b010,0b110,0b010,0b010,0b111}, // 1
  {0b111,0b001,0b111,0b100,0b111}, // 2
  {0b111,0b001,0b111,0b001,0b111}, // 3
  {0b101,0b101,0b111,0b001,0b001}, // 4
  {0b111,0b100,0b111,0b001,0b111}, // 5
  {0b111,0b100,0b111,0b101,0b111}, // 6
  {0b111,0b001,0b010,0b010,0b010}, // 7
  {0b111,0b101,0b111,0b101,0b111}, // 8
  {0b111,0b101,0b111,0b001,0b111}, // 9
};

uint8_t frame[8][12];
int dispMode = 0;    // 0=aus, 1=dB(Pegel), 2=BPM
int dispValue = 0;

void clearFrame(){ for(int r=0;r<8;r++) for(int c=0;c<12;c++) frame[r][c]=0; }
void px(int x,int y){ if(x>=0&&x<12&&y>=0&&y<8) frame[y][x]=1; }

void drawDigit(int d,int x,int yTop){
  if(d<0||d>9) return;
  for(int r=0;r<5;r++){
    uint8_t b=FONT[d][r];
    if(b&0b100) px(x,   yTop+r);
    if(b&0b010) px(x+1, yTop+r);
    if(b&0b001) px(x+2, yTop+r);
  }
}

void drawNumber(int v,int yTop){
  if(v<0) v=0; if(v>999) v=999;
  char s[6]; snprintf(s,sizeof(s),"%d",v);
  int n=strlen(s);
  int w=n*3+(n-1);          // 3px/Ziffer + 1px Luecke
  int x=(12-w)/2;
  for(int i=0;i<n;i++){ drawDigit(s[i]-'0',x,yTop); x+=4; }
}

void drawIndicator(){
  if(dispMode==1){ px(0,0);px(1,0);px(0,1);px(1,1); }        // dB: 2x2 oben links
  else if(dispMode==2){ px(11,1);px(10,0);px(9,1); }         // BPM: Spitze oben rechts
}

void updateDisplay(){
  clearFrame();
  if(dispMode!=0){ drawIndicator(); drawNumber(dispValue,3); }
  matrix.renderBitmap(frame,8,12);
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
  while(Serial.available()){
    char c=Serial.read();
    if(c==13||c==10){
      buf.trim();
      if(buf.length()>0){
        char k=buf.charAt(0);
        if(k=='m'){ dispMode=buf.substring(1).toInt(); updateDisplay(); Serial.print(F("M")); Serial.println(dispMode); }
        else if(k=='v'){ dispValue=buf.substring(1).toInt(); updateDisplay(); }
        else { long val=strtol(buf.c_str(),NULL,16); IrSender.sendNEC(TEUFEL_ADDR,(uint8_t)val,0); Serial.print(F("TX 0x")); Serial.println((uint8_t)val,HEX); }
      }
      buf="";
    } else if(buf.length()<8){ buf+=c; }
  }
}
