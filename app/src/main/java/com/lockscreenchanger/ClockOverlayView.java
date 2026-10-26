package com.lockscreenchanger;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Typeface;
import android.text.format.DateFormat;
import android.util.AttributeSet;
import android.view.View;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

import java.util.Locale;

/**
 * A lock screen style clock drawn over the preview, sized relative to the frame, so you can see
 * whether the clock will cover anything important.
 */
public class ClockOverlayView extends View {

    private static final int SHADOW_COLOR = Color.argb(110, 0, 0, 0);

    private final Paint timePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint datePaint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Runnable tick = this::onTick;

    private String time = "";
    private String date = "";

    public ClockOverlayView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        timePaint.setColor(Color.WHITE);
        timePaint.setTextAlign(Paint.Align.CENTER);
        timePaint.setTypeface(Typeface.create("sans-serif-light", Typeface.NORMAL));
        datePaint.setColor(Color.WHITE);
        datePaint.setTextAlign(Paint.Align.CENTER);
        datePaint.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
    }

    @Override
    protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        onTick();
    }

    @Override
    protected void onDetachedFromWindow() {
        removeCallbacks(tick);
        super.onDetachedFromWindow();
    }

    private void onTick() {
        long now = System.currentTimeMillis();
        time = DateFormat.format(DateFormat.is24HourFormat(getContext()) ? "H:mm" : "h:mm", now)
                .toString();
        date = DateFormat.format(
                DateFormat.getBestDateTimePattern(Locale.getDefault(), "EEEMMMd"), now).toString();
        invalidate();
        removeCallbacks(tick);
        postDelayed(tick, 60_000 - now % 60_000);
    }

    @Override
    protected void onDraw(@NonNull Canvas canvas) {
        float height = getHeight();
        float centerX = getWidth() / 2f;
        float shadow = height * 0.004f;

        timePaint.setTextSize(height * 0.09f);
        timePaint.setShadowLayer(shadow * 2, 0, shadow, SHADOW_COLOR);
        datePaint.setTextSize(height * 0.022f);
        datePaint.setShadowLayer(shadow * 2, 0, shadow, SHADOW_COLOR);

        float timeBaseline = height * 0.2f;
        canvas.drawText(time, centerX, timeBaseline, timePaint);
        canvas.drawText(date, centerX, timeBaseline + height * 0.04f, datePaint);
    }
}
