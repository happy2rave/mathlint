package io.github.happy2rave.mathlint;

import android.os.Bundle;
import androidx.activity.EdgeToEdge;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // The page draws behind the status and navigation bars on every Android
        // version (15 and newer insist on it) and keeps clear of them with the
        // insets Capacitor passes it (capacitor.config.json, SystemBars).
        EdgeToEdge.enable(this);
    }
}
