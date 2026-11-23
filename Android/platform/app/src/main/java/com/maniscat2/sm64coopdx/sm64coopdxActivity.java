package com.maniscat2.sm64coopdx;

import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.ViewTreeObserver;
import android.widget.LinearLayout;
import android.widget.TextView;

import org.libsdl.app.SDLActivity;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;

public class sm64coopdxActivity extends SDLActivity {
    private View startupOverlay;
    private TextView startupStatus;
    private final CountDownLatch startupDrawn = new CountDownLatch(1);

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (mLayout == null || mBrokenLibraries) return;
        LinearLayout overlay = new LinearLayout(this);
        overlay.setOrientation(LinearLayout.VERTICAL);
        overlay.setGravity(Gravity.CENTER);
        overlay.setBackgroundColor(Color.rgb(23, 2, 34));
        TextView title = new TextView(this);
        title.setText("GOREMOD IS DOING STUFF!!!");
        title.setTextColor(Color.MAGENTA);
        title.setTextSize(28);
        title.setGravity(Gravity.CENTER);
        startupStatus = new TextView(this);
        startupStatus.setText("Copying game stuff... please hold lol");
        startupStatus.setTextColor(Color.YELLOW);
        startupStatus.setTextSize(20);
        startupStatus.setGravity(Gravity.CENTER);
        overlay.addView(title);
        overlay.addView(startupStatus);
        startupOverlay = overlay;
        mLayout.addView(overlay, new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        overlay.getViewTreeObserver().addOnDrawListener(new ViewTreeObserver.OnDrawListener() {
            @Override public void onDraw() { startupDrawn.countDown(); }
        });
    }

    // Called on SDL's native thread, never on the UI thread. Bound the wait so
    // a paused or destroyed activity cannot hang startup indefinitely.
    public void awaitStartupOverlay() {
        try { startupDrawn.await(2, TimeUnit.SECONDS); }
        catch (InterruptedException e) { Thread.currentThread().interrupt(); }
    }
    public void setStartupStatus(final String text) {
        runOnUiThread(() -> { if (startupStatus != null) startupStatus.setText(text); });
    }
    public void hideStartupOverlay() {
        runOnUiThread(() -> {
            if (startupOverlay != null) {
                ViewGroup parent = (ViewGroup) startupOverlay.getParent();
                if (parent != null) parent.removeView(startupOverlay);
                startupOverlay = null;
                startupStatus = null;
            }
        });
    }
}
