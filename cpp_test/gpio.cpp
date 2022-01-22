#include<stdio.h>
#include<stdlib.h>
#include <wiringPi.h>
using namespace std;
int main(void)
{
  wiringPiSetup();
  pinMode(0, OUTPUT);
  for(;;)
  {
    digitalWrite(0, HIGH);
    // printf("LED ON\n"); 
    delay(100);
    digitalWrite(0, LOW);
    // printf("LED OFF\n");
    delay(100);
  }
}