void sanityTest(GeneralController** controllers, int count) {
    Serial.println(F("========== SANITY TESTS =========="));

    for (int i = 0; i < count; i++) {
        if (controllers[i] != nullptr) {
            controllers[i]->sanityTest();
        }
    }
    Serial.println(F("========== TESTS COMPLETE =========="));
}