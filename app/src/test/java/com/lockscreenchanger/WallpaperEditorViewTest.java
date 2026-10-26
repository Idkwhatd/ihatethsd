package com.lockscreenchanger;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.os.Bundle;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.GraphicsMode;

@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
public class WallpaperEditorViewTest {

    /** Wallpaper size used throughout: a 1:2 screen. */
    private static final int WIDTH = 100;
    private static final int HEIGHT = 200;

    private WallpaperEditorView editor;

    @Before
    public void setUp() {
        editor = new WallpaperEditorView(RuntimeEnvironment.getApplication(), null);
        editor.setFrameAspect((float) WIDTH / HEIGHT);
        editor.layout(0, 0, WIDTH, HEIGHT);
        // A 2:1 landscape photo: left half red, right half blue.
        editor.setPhoto(WallpaperEditorView.Photo.from(halves(400, 200)), null);
    }

    @Test
    public void defaultFillsScreenWithCenterOfPhoto() {
        Bitmap wallpaper = render();
        assertColor(Color.RED, wallpaper.getPixel(20, 100));
        assertColor(Color.BLUE, wallpaper.getPixel(80, 100));
        assertFalse(editor.leavesGaps());
        assertTrue(editor.canFit());
    }

    @Test
    public void panningStopsAtPhotoEdge() {
        editor.pan(10_000, 10_000);
        Bitmap wallpaper = render();
        // Dragged as far right as it goes: the left (red) edge of the photo fills the screen.
        assertColor(Color.RED, wallpaper.getPixel(2, 2));
        assertColor(Color.RED, wallpaper.getPixel(97, 197));
    }

    @Test
    public void zoomingOutShowsWholePhotoOnBackground() {
        Bundle state = editor.saveState();
        state.putFloat("zoom", 0f);
        state.putInt("background", WallpaperEditorView.BACKGROUND_BLACK);
        editor.setPhoto(WallpaperEditorView.Photo.from(halves(400, 200)), state);

        Bitmap wallpaper = render();
        assertTrue(editor.leavesGaps());
        // The photo shrinks to 100x50, centred vertically, with black above and below.
        assertColor(Color.BLACK, wallpaper.getPixel(50, 20));
        assertColor(Color.BLACK, wallpaper.getPixel(50, 180));
        assertColor(Color.RED, wallpaper.getPixel(20, 100));
        assertColor(Color.BLUE, wallpaper.getPixel(80, 100));
    }

    @Test
    public void rotatingTurnsPhotoClockwise() {
        editor.rotate();
        Bitmap wallpaper = render();
        // The rotated photo is 1:2 like the screen, so it fits exactly: red on top, blue below.
        assertColor(Color.RED, wallpaper.getPixel(50, 40));
        assertColor(Color.BLUE, wallpaper.getPixel(50, 160));
        assertFalse(editor.canFit());
    }

    @Test
    public void zoomingKeepsPointUnderFingersInPlace() {
        // Zoom in 2x around the red/blue boundary at the screen centre.
        editor.zoomBy(2f, WIDTH / 2f, HEIGHT / 2f);
        Bitmap wallpaper = render();
        assertColor(Color.RED, wallpaper.getPixel(40, 100));
        assertColor(Color.BLUE, wallpaper.getPixel(60, 100));
    }

    @Test
    public void dimDarkensWallpaper() {
        editor.setDim(0.5f);
        int pixel = render().getPixel(20, 100);
        assertEquals(128, Color.red(pixel), 3);
        assertEquals(0, Color.blue(pixel), 3);
    }

    @Test
    public void resetRestoresDefaults() {
        editor.rotate();
        editor.setDim(0.4f);
        editor.reset();
        assertEquals(0f, editor.getDim(), 0f);
        assertColor(Color.RED, render().getPixel(20, 100));
    }

    @Test
    public void largeOutputsAreRenderedFromFullResolutionPhoto() {
        Bitmap wallpaper = editor.snapshot().render(1080, 2160);
        assertEquals(1080, wallpaper.getWidth());
        assertEquals(2160, wallpaper.getHeight());
        assertColor(Color.RED, wallpaper.getPixel(200, 1080));
        assertColor(Color.BLUE, wallpaper.getPixel(880, 1080));
    }

    private Bitmap render() {
        return editor.snapshot().render(WIDTH, HEIGHT);
    }

    private static Bitmap halves(int width, int height) {
        Bitmap bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint();
        paint.setColor(Color.RED);
        canvas.drawRect(0, 0, width / 2f, height, paint);
        paint.setColor(Color.BLUE);
        canvas.drawRect(width / 2f, 0, width, height, paint);
        return bitmap;
    }

    private static void assertColor(int expected, int actual) {
        String message = String.format("expected #%08X but was #%08X", expected, actual);
        assertEquals(message, Color.red(expected), Color.red(actual), 8);
        assertEquals(message, Color.green(expected), Color.green(actual), 8);
        assertEquals(message, Color.blue(expected), Color.blue(actual), 8);
    }
}
