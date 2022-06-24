/* This program is used to calibrate analog sensors, such as those for moisture or rain.
 * Please connect the sensor as it is supposed to be to the board. You will also need a glass of water.
 * Run this program twice: first with the sensor in the air/on a dry surface; it should return 4095. This is the value 
 * for 0% rain/moisture, termed "MOISTURE_AIR/RAIN_DRY" Precision-Agriculture-Board sketches.. Next, submerge the sensor in water: Not to deep though! No cables should be touching water. 
 * See photos in readme for instructions.
 * Then, run the program with the sensor submerged. This will yield the values for 100% rain/moisture, termed "MOISTURE_WATER/RAIN_WET" in 
 * Precision-Agriculture-Board sketches.
 * The values will be visualized on the Serial Monitor.
 */

#define SENSOR_PIN 33
#define NUMBER_MEASUREMENTS 20
#define CALIBRATION_SECONDS 30
int i=0;
int min_val;
int max_val;
int mean_val;
int len;
int measurements[NUMBER_MEASUREMENTS];
void setup(){
  Serial.begin(115200);
  Serial.print("Waiting ");
  Serial.print(CALIBRATION_SECONDS);
  Serial.println(" seconds for stabilized measurement");
  for(i=0;i<CALIBRATION_SECONDS;i++){
    Serial.print(i);
    Serial.print(", ");
    delay(1000);
  }  
  Serial.println();
  for(i=0;i<NUMBER_MEASUREMENTS;i++){
  measurements[i] = analogRead(SENSOR_PIN);
  Serial.println(measurements[i]);
  delay(1000);
  }
  len = sizeof(measurements)/sizeof(measurements[0]);
  Serial.println("==============");
  min_val = min_array(measurements,len);
  max_val = max_array(measurements,len);
  mean_val = mean_array(measurements,len);
  Serial.print("Min: ");
  Serial.println(min_val);
  Serial.print("Max: ");
  Serial.println(max_val);
  Serial.print("Mean: ");
  Serial.println(mean_val);
}
void loop(){

}

int min_array(int measurements[], int len){
  int min_value = measurements[0] ; 
  int index = 0 ;                
  for (int i = 1; i<len; i++) // Changed this.
  {
    if (measurements[i] < min_value) {
         index = i;
         min_value = measurements[i];
    }
  }
  return min_value;
}

int max_array(int measurements[], int len) {
  int max_value = measurements[0] ; 
  int index = 0 ;                
  for (int i = 1; i<len; i++) // Changed this.
  {
    if (measurements[i] > max_value) {
         index = i;
         max_value = measurements[i];
    }
  }
  return max_value;
}
float mean_array(int measurements[], int len){
  float mean_value = 0;
  int sum_value = measurements[0]; 
  int index = 0 ;                
  for (int i = 1; i<len; i++) // Changed this.
  {
  sum_value = sum_value + measurements[i];
  }
  mean_value = sum_value / float(len);
  return mean_value;
}
