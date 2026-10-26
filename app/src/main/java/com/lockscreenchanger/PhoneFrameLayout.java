package com.lockscreenchanger;

import android.content.Context;
import android.graphics.Outline;
import android.util.AttributeSet;
import android.view.View;
import android.view.ViewOutlineProvider;
import android.widget.FrameLayout;

import androidx.annotation.Nullable;

/**
 * A frame with the phone screen's shape: it takes the largest size with the screen's aspect ratio
 * that fits, and clips its children to rounded corners.
 */
public class PhoneFrameLayout extends FrameLayout {

    /** Corner radius as a fraction of the frame width, roughly matching modern phones. */
    private static final float CORNER_FRACTION = 0.08f;

    private float aspectRatio = 9f / 19.5f;

    public PhoneFrameLayout(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        setClipToOutline(true);
        setOutlineProvider(new ViewOutlineProvider() {
            @Override
            public void getOutline(View view, Outline outline) {
                outline.setRoundRect(0, 0, view.getWidth(), view.getHeight(),
                        CORNER_FRACTION * view.getWidth());
            }
        });
    }

    /** Width / height of the screen. */
    public void setAspectRatio(float aspectRatio) {
        this.aspectRatio = aspectRatio;
        requestLayout();
    }

    @Override
    protected void onMeasure(int widthMeasureSpec, int heightMeasureSpec) {
        int width = MeasureSpec.getSize(widthMeasureSpec);
        int height = Math.round(width / aspectRatio);
        int maxHeight = MeasureSpec.getSize(heightMeasureSpec);
        if (height > maxHeight) {
            height = maxHeight;
            width = Math.round(height * aspectRatio);
        }
        super.onMeasure(MeasureSpec.makeMeasureSpec(width, MeasureSpec.EXACTLY),
                MeasureSpec.makeMeasureSpec(height, MeasureSpec.EXACTLY));
    }

    @Override
    protected void onSizeChanged(int w, int h, int oldw, int oldh) {
        super.onSizeChanged(w, h, oldw, oldh);
        invalidateOutline();
    }
}
