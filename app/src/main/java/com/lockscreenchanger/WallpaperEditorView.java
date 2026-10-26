package com.lockscreenchanger;

import android.animation.ValueAnimator;
import android.annotation.SuppressLint;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Matrix;
import android.graphics.Paint;
import android.os.Bundle;
import android.util.AttributeSet;
import android.view.GestureDetector;
import android.view.MotionEvent;
import android.view.ScaleGestureDetector;
import android.view.View;
import android.view.animation.DecelerateInterpolator;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;

/**
 * Shows the photo in a phone-screen-shaped frame and lets the user drag, pinch-zoom and rotate it.
 * The same adjustments render the final wallpaper at full screen resolution.
 */
public class WallpaperEditorView extends View {

    public static final int BACKGROUND_BLUR = 0;
    public static final int BACKGROUND_BLACK = 1;
    public static final int BACKGROUND_WHITE = 2;

    private static final float MAX_ZOOM = 5f;
    private static final float EPSILON = 0.001f;
    /** Long side of the copy drawn on screen; the full-size photo is only used for the wallpaper. */
    private static final int MAX_PREVIEW_SIDE = 2048;
    /** Short side of the tiny copy that is blurred and stretched behind a photo that doesn't fill the screen. */
    private static final int BLUR_SIDE = 32;
    private static final int BLUR_SCRIM = Color.argb(48, 0, 0, 0);

    public interface OnChangeListener {
        void onEditorChanged();
    }

    /** A decoded photo plus the smaller copies used for the on-screen preview and blurred background. */
    public static final class Photo {
        final Bitmap full;
        final Bitmap preview;
        final Bitmap blurred;

        private Photo(Bitmap full, Bitmap preview, Bitmap blurred) {
            this.full = full;
            this.preview = preview;
            this.blurred = blurred;
        }

        /** Prepares the preview copies. Slow for big photos, so call it off the UI thread. */
        public static Photo from(Bitmap full) {
            Bitmap preview = full;
            while (Math.max(preview.getWidth(), preview.getHeight()) > MAX_PREVIEW_SIDE) {
                preview = halve(preview);
            }
            return new Photo(full, preview, blur(preview));
        }
    }

    /** Everything the user can adjust. Positions are relative, so they apply at any output size. */
    static final class State {
        /** Clockwise rotation: 0, 90, 180 or 270 degrees. */
        int rotation;
        /** 1 means the photo exactly covers the screen; less leaves gaps, more crops in. */
        float zoom = 1f;
        /** Point of the rotated photo (0..1 across each side) shown at the centre of the screen. */
        float focusX = 0.5f;
        float focusY = 0.5f;
        /** Opacity of the black overlay, 0..1. */
        float dim;
        int background = BACKGROUND_BLUR;

        State copy() {
            return fromBundle(toBundle());
        }

        Bundle toBundle() {
            Bundle bundle = new Bundle();
            bundle.putInt("rotation", rotation);
            bundle.putFloat("zoom", zoom);
            bundle.putFloat("focusX", focusX);
            bundle.putFloat("focusY", focusY);
            bundle.putFloat("dim", dim);
            bundle.putInt("background", background);
            return bundle;
        }

        static State fromBundle(Bundle bundle) {
            State state = new State();
            state.rotation = bundle.getInt("rotation", 0);
            state.zoom = bundle.getFloat("zoom", 1f);
            state.focusX = bundle.getFloat("focusX", 0.5f);
            state.focusY = bundle.getFloat("focusY", 0.5f);
            state.dim = bundle.getFloat("dim", 0f);
            state.background = bundle.getInt("background", BACKGROUND_BLUR);
            return state;
        }
    }

    /** The photo and adjustments at one moment, so the wallpaper can be rendered off the UI thread. */
    public static final class Renderer {
        private final Photo photo;
        private final State state;

        Renderer(Photo photo, State state) {
            this.photo = photo;
            this.state = state;
        }

        public Bitmap render(int width, int height) {
            Bitmap source = photo.full;
            // Bilinear filtering gets grainy when shrinking by more than half in one step, so
            // shrink the photo in halves first, like a mipmap.
            while (coverScale(source, state.rotation, width, height) * state.zoom < 0.5f
                    && source.getWidth() > 1 && source.getHeight() > 1) {
                source = halve(source);
            }
            Bitmap wallpaper = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
            draw(new Canvas(wallpaper), width, height, source, photo.blurred, state,
                    new Matrix(), newBitmapPaint());
            return wallpaper;
        }
    }

    private final Matrix matrix = new Matrix();
    private final Paint paint = newBitmapPaint();
    private final ScaleGestureDetector scaleDetector;
    private final GestureDetector gestureDetector;

    private Photo photo;
    private State state = new State();
    private float frameAspect = 9f / 19.5f;
    private ValueAnimator zoomAnimator;
    private OnChangeListener listener;

    public WallpaperEditorView(Context context, @Nullable AttributeSet attrs) {
        super(context, attrs);
        scaleDetector = new ScaleGestureDetector(context,
                new ScaleGestureDetector.SimpleOnScaleGestureListener() {
                    @Override
                    public boolean onScale(@NonNull ScaleGestureDetector detector) {
                        zoomBy(detector.getScaleFactor(), detector.getFocusX(), detector.getFocusY());
                        return true;
                    }
                });
        // Double-tap toggles fit/fill, which would fight with double-tap-and-drag zooming.
        scaleDetector.setQuickScaleEnabled(false);
        gestureDetector = new GestureDetector(context, new GestureDetector.SimpleOnGestureListener() {
            @Override
            public boolean onDown(@NonNull MotionEvent e) {
                return true;
            }

            @Override
            public boolean onScroll(@Nullable MotionEvent e1, @NonNull MotionEvent e2,
                    float distanceX, float distanceY) {
                pan(-distanceX, -distanceY);
                return true;
            }

            @Override
            public boolean onDoubleTap(@NonNull MotionEvent e) {
                toggleFit();
                return true;
            }

            @Override
            public boolean onSingleTapConfirmed(@NonNull MotionEvent e) {
                return performClick();
            }
        });
    }

    public void setOnChangeListener(OnChangeListener listener) {
        this.listener = listener;
    }

    /** Width / height of the screen the wallpaper is for; this view is laid out at the same ratio. */
    public void setFrameAspect(float aspect) {
        frameAspect = aspect;
        if (photo != null) {
            clampState();
            changed();
        }
    }

    public void setPhoto(Photo photo, @Nullable Bundle savedState) {
        cancelAnimation();
        this.photo = photo;
        state = savedState != null ? State.fromBundle(savedState) : new State();
        clampState();
        changed();
    }

    public boolean hasPhoto() {
        return photo != null;
    }

    public Bundle saveState() {
        return state.toBundle();
    }

    public Renderer snapshot() {
        return new Renderer(photo, state.copy());
    }

    public void rotate() {
        if (photo == null) {
            return;
        }
        cancelAnimation();
        // Keep the same part of the photo centred: rotating clockwise maps (x, y) to (1 - y, x).
        float focusX = state.focusX;
        state.focusX = 1f - state.focusY;
        state.focusY = focusX;
        state.rotation = (state.rotation + 90) % 360;
        clampState();
        changed();
    }

    /** Switches between showing the whole photo and filling the screen with it. */
    public void toggleFit() {
        if (photo != null) {
            animateZoomTo(leavesGaps() ? 1f : minZoom());
        }
    }

    /** Whether the photo is zoomed out far enough that it doesn't cover the whole screen. */
    public boolean leavesGaps() {
        return photo != null && state.zoom < 1f - EPSILON;
    }

    /** Whether fitting would change anything, i.e. the photo's shape differs from the screen's. */
    public boolean canFit() {
        return photo != null && minZoom() < 1f - EPSILON;
    }

    public void reset() {
        cancelAnimation();
        state = new State();
        clampState();
        changed();
    }

    public float getDim() {
        return state.dim;
    }

    public void setDim(float dim) {
        state.dim = dim;
        changed();
    }

    public int getBackgroundMode() {
        return state.background;
    }

    public void setBackgroundMode(int background) {
        if (state.background != background) {
            state.background = background;
            changed();
        }
    }

    @Override
    protected void onDraw(@NonNull Canvas canvas) {
        if (photo != null) {
            draw(canvas, getWidth(), getHeight(), photo.preview, photo.blurred, state, matrix, paint);
        }
    }

    @SuppressLint("ClickableViewAccessibility") // Taps reach performClick via the gesture detector.
    @Override
    public boolean onTouchEvent(MotionEvent event) {
        if (photo == null || !isEnabled()) {
            return false;
        }
        if (event.getActionMasked() == MotionEvent.ACTION_DOWN) {
            cancelAnimation();
            getParent().requestDisallowInterceptTouchEvent(true);
        }
        scaleDetector.onTouchEvent(event);
        gestureDetector.onTouchEvent(event);
        return true;
    }

    @Override
    public boolean performClick() {
        return super.performClick();
    }

    /** Moves the photo by a finger movement of ({@code dx}, {@code dy}) pixels. */
    void pan(float dx, float dy) {
        if (photo == null || getWidth() == 0) {
            return;
        }
        state.focusX -= dx / (relativeWidth() * getWidth());
        state.focusY -= dy / (relativeHeight() * getHeight());
        clampState();
        changed();
    }

    /** Zooms by {@code factor}, keeping the part of the photo under (px, py) in place. */
    void zoomBy(float factor, float px, float py) {
        if (photo == null || getWidth() == 0) {
            return;
        }
        float offsetX = px - getWidth() / 2f;
        float offsetY = py - getHeight() / 2f;
        float anchorX = state.focusX + offsetX / (relativeWidth() * getWidth());
        float anchorY = state.focusY + offsetY / (relativeHeight() * getHeight());
        state.zoom = Math.max(minZoom(), Math.min(MAX_ZOOM, state.zoom * factor));
        state.focusX = anchorX - offsetX / (relativeWidth() * getWidth());
        state.focusY = anchorY - offsetY / (relativeHeight() * getHeight());
        clampState();
        changed();
    }

    private void animateZoomTo(float target) {
        cancelAnimation();
        zoomAnimator = ValueAnimator.ofFloat(state.zoom, target);
        zoomAnimator.setDuration(250);
        zoomAnimator.setInterpolator(new DecelerateInterpolator());
        zoomAnimator.addUpdateListener(animator -> {
            state.zoom = (float) animator.getAnimatedValue();
            clampState();
            changed();
        });
        zoomAnimator.start();
    }

    private void cancelAnimation() {
        if (zoomAnimator != null) {
            zoomAnimator.cancel();
            zoomAnimator = null;
        }
    }

    private void changed() {
        invalidate();
        if (listener != null) {
            listener.onEditorChanged();
        }
    }

    /** The photo's width / height after rotation. */
    private float rotatedAspect() {
        Bitmap bitmap = photo.full;
        return state.rotation % 180 == 0
                ? (float) bitmap.getWidth() / bitmap.getHeight()
                : (float) bitmap.getHeight() / bitmap.getWidth();
    }

    /** The zoom at which the whole photo just fits on screen. */
    private float minZoom() {
        float aspect = rotatedAspect();
        return Math.min(aspect / frameAspect, frameAspect / aspect);
    }

    /** The photo's on-screen width as a multiple of the screen width. */
    private float relativeWidth() {
        return state.zoom * Math.max(1f, rotatedAspect() / frameAspect);
    }

    /** The photo's on-screen height as a multiple of the screen height. */
    private float relativeHeight() {
        return state.zoom * Math.max(1f, frameAspect / rotatedAspect());
    }

    private void clampState() {
        state.zoom = Math.max(minZoom(), Math.min(MAX_ZOOM, state.zoom));
        state.focusX = clampFocus(state.focusX, relativeWidth());
        state.focusY = clampFocus(state.focusY, relativeHeight());
    }

    /** Keeps the photo's edges off screen, or centres it along a side where it's smaller than the screen. */
    private static float clampFocus(float focus, float relativeSize) {
        if (relativeSize <= 1f) {
            return 0.5f;
        }
        float slack = (relativeSize - 1f) / (2f * relativeSize);
        return Math.max(0.5f - slack, Math.min(0.5f + slack, focus));
    }

    private static void draw(Canvas canvas, int width, int height, Bitmap image, Bitmap blurred,
            State state, Matrix matrix, Paint paint) {
        switch (state.background) {
            case BACKGROUND_BLACK:
                canvas.drawColor(Color.BLACK);
                break;
            case BACKGROUND_WHITE:
                canvas.drawColor(Color.WHITE);
                break;
            default:
                setMatrix(matrix, blurred, state.rotation, 1f, 0.5f, 0.5f, width, height);
                canvas.drawBitmap(blurred, matrix, paint);
                canvas.drawColor(BLUR_SCRIM);
                break;
        }
        setMatrix(matrix, image, state.rotation, state.zoom, state.focusX, state.focusY, width, height);
        canvas.drawBitmap(image, matrix, paint);
        if (state.dim > 0f) {
            canvas.drawColor(Color.argb(Math.round(state.dim * 255), 0, 0, 0));
        }
    }

    /**
     * Maps {@code bitmap}, rotated, so that at zoom 1 it just covers a {@code width} x
     * {@code height} canvas, with the point (focusX, focusY) of the rotated bitmap at the centre.
     */
    private static void setMatrix(Matrix matrix, Bitmap bitmap, int rotation, float zoom,
            float focusX, float focusY, int width, int height) {
        boolean sideways = rotation % 180 != 0;
        float rotatedWidth = sideways ? bitmap.getHeight() : bitmap.getWidth();
        float rotatedHeight = sideways ? bitmap.getWidth() : bitmap.getHeight();
        float scale = coverScale(bitmap, rotation, width, height) * zoom;
        matrix.reset();
        matrix.postTranslate(-bitmap.getWidth() / 2f, -bitmap.getHeight() / 2f);
        matrix.postRotate(rotation);
        matrix.postScale(scale, scale);
        matrix.postTranslate(width / 2f - (focusX - 0.5f) * rotatedWidth * scale,
                height / 2f - (focusY - 0.5f) * rotatedHeight * scale);
    }

    /** Scale at which {@code bitmap}, rotated, just covers a {@code width} x {@code height} canvas. */
    private static float coverScale(Bitmap bitmap, int rotation, int width, int height) {
        boolean sideways = rotation % 180 != 0;
        float rotatedWidth = sideways ? bitmap.getHeight() : bitmap.getWidth();
        float rotatedHeight = sideways ? bitmap.getWidth() : bitmap.getHeight();
        return Math.max(width / rotatedWidth, height / rotatedHeight);
    }

    private static Paint newBitmapPaint() {
        return new Paint(Paint.FILTER_BITMAP_FLAG | Paint.ANTI_ALIAS_FLAG);
    }

    /** Half-size copy; at exactly 2:1, bilinear filtering averages each 2x2 block. */
    private static Bitmap halve(Bitmap bitmap) {
        return Bitmap.createScaledBitmap(bitmap, Math.max(1, bitmap.getWidth() / 2),
                Math.max(1, bitmap.getHeight() / 2), true);
    }

    /** Tiny, softly blurred copy of {@code source}; stretched up, it makes a smooth backdrop. */
    private static Bitmap blur(Bitmap source) {
        float scale = (float) BLUR_SIDE / Math.min(source.getWidth(), source.getHeight());
        int width = Math.max(1, Math.round(source.getWidth() * scale));
        int height = Math.max(1, Math.round(source.getHeight() * scale));
        int[] pixels = new int[width * height];
        Bitmap.createScaledBitmap(source, width, height, true)
                .getPixels(pixels, 0, width, 0, 0, width, height);
        for (int pass = 0; pass < 2; pass++) {
            boxBlur(pixels, width, height, true);
            boxBlur(pixels, width, height, false);
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
    }

    private static void boxBlur(int[] pixels, int width, int height, boolean horizontal) {
        final int radius = 2;
        int length = horizontal ? width : height;
        int lines = horizontal ? height : width;
        int[] line = new int[length];
        for (int l = 0; l < lines; l++) {
            for (int i = 0; i < length; i++) {
                line[i] = pixels[horizontal ? l * width + i : i * width + l];
            }
            for (int i = 0; i < length; i++) {
                int red = 0, green = 0, blue = 0, count = 0;
                for (int k = Math.max(0, i - radius); k <= Math.min(length - 1, i + radius); k++) {
                    red += Color.red(line[k]);
                    green += Color.green(line[k]);
                    blue += Color.blue(line[k]);
                    count++;
                }
                pixels[horizontal ? l * width + i : i * width + l] =
                        Color.rgb(red / count, green / count, blue / count);
            }
        }
    }
}
