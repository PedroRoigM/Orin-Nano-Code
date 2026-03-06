const int trigPin_1 = 38;
const int echoPin_1 =39;

const int trigPin_2 = 40;
const int echoPin_2 = 41;

float duration, distance;

void setup()
{
  pinMode(trigPin_1, OUTPUT);
  pinMode(echoPin_1, INPUT);
  pinMode(trigPin_2, OUTPUT);
  pinMode(echoPin_2, INPUT);
  Serial.begin(9600);
}

void loop()
{
  digitalWrite(trigPin_1, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin_1, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin_1, LOW);

  duration = pulseIn(echoPin_1, HIGH);
  distance = (duration * .0343) / 2;
  Serial.print("US 1: ");
  Serial.println(distance);

    digitalWrite(trigPin_2, LOW);
  delayMicroseconds(2);
  digitalWrite(trigPin_2, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin_2, LOW);

  duration = pulseIn(echoPin_2, HIGH);
  distance = (duration * .0343) / 2;
  Serial.print("US 2: ");
  Serial.println(distance);
  delay(1000);
}