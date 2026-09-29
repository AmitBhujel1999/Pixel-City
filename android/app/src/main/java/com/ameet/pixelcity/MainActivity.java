package com.ameet.pixelcity;

import android.os.Build;
import android.os.Bundle;
import android.view.DisplayCutout;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowManager;
import android.webkit.WebView;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        // Keep the screen awake while playing.
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        // Draw into the notch / punch-hole area so the game fills the whole screen on every phone.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            WindowManager.LayoutParams lp = getWindow().getAttributes();
            lp.layoutInDisplayCutoutMode = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                ? WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_ALWAYS
                : WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
            getWindow().setAttributes(lp);
        }
        hideSystemBars();
        View decor = getWindow().getDecorView();
        decor.setOnApplyWindowInsetsListener((v, insets) -> {
            sendSafeArea(insets);
            return v.onApplyWindowInsets(insets);
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        hideSystemBars();
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {
            hideSystemBars();
            WindowInsets insets = getWindow().getDecorView().getRootWindowInsets();
            if (insets != null) sendSafeArea(insets);
        }
    }

    private void hideSystemBars() {
        WindowCompat.setDecorFitsSystemWindows(getWindow(), false);
        WindowInsetsControllerCompat c = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
        c.hide(WindowInsetsCompat.Type.systemBars());
        c.setSystemBarsBehavior(WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
    }

    /** Tell the game where the camera cutout is, so buttons stay clear of it. */
    private void sendSafeArea(WindowInsets insets) {
        int l = 0, t = 0, r = 0, b = 0;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            DisplayCutout cut = insets.getDisplayCutout();
            if (cut != null) {
                l = cut.getSafeInsetLeft(); t = cut.getSafeInsetTop();
                r = cut.getSafeInsetRight(); b = cut.getSafeInsetBottom();
            }
        }
        float d = getResources().getDisplayMetrics().density;
        final String js = String.format(java.util.Locale.US,
            "(function(){var s=document.documentElement.style;s.setProperty('--sal','%.1fpx');s.setProperty('--sat','%.1fpx');s.setProperty('--sar','%.1fpx');s.setProperty('--sab','%.1fpx');window.dispatchEvent(new Event('resize'));})()",
            l / d, t / d, r / d, b / d);
        if (getBridge() == null) return;
        final WebView wv = getBridge().getWebView();
        if (wv != null) wv.post(() -> wv.evaluateJavascript(js, null));
    }
}
