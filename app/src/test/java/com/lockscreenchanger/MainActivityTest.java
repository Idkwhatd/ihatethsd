package com.lockscreenchanger;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.robolectric.Shadows.shadowOf;

import android.app.Dialog;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Shader;
import android.net.Uri;
import android.os.Looper;
import android.view.View;

import com.google.android.material.button.MaterialButton;

import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.Robolectric;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.android.controller.ActivityController;
import org.robolectric.annotation.Config;
import org.robolectric.annotation.GraphicsMode;
import org.robolectric.shadows.ShadowDialog;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;

/** Drives the screen and saves screenshots to app/build/screenshots for eyeballing the layout. */
@RunWith(RobolectricTestRunner.class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(qualifiers = "w411dp-h914dp-port-xxhdpi")
public class MainActivityTest {

    @Test
    public void emptyStateAsksForPhoto() throws IOException {
        MainActivity activity = Robolectric.buildActivity(MainActivity.class).setup().get();
        idle();

        assertEquals(View.VISIBLE, activity.findViewById(R.id.empty_state).getVisibility());
        assertFalse(activity.findViewById(R.id.apply_button).isEnabled());
        assertFalse(activity.findViewById(R.id.rotate_button).isEnabled());
        assertEquals(activity.getString(R.string.choose_photo),
                ((MaterialButton) activity.findViewById(R.id.photo_button)).getText().toString());
        screenshot(activity.getWindow().getDecorView(), "1-empty");
    }

    @Test
    public void photoCanBeEditedAndApplied() throws IOException {
        ActivityController<MainActivity> controller =
                Robolectric.buildActivity(MainActivity.class).setup();
        MainActivity activity = controller.get();
        activity.showPhoto(Uri.parse("content://test/photo"),
                WallpaperEditorView.Photo.from(landscape()), null);
        idle();

        assertEquals(View.GONE, activity.findViewById(R.id.empty_state).getVisibility());
        assertEquals(View.VISIBLE, activity.findViewById(R.id.clock_overlay).getVisibility());
        assertTrue(activity.findViewById(R.id.apply_button).isEnabled());
        screenshot(activity.getWindow().getDecorView(), "2-photo");

        // Fit the whole landscape photo and dim it a bit.
        WallpaperEditorView editor = activity.findViewById(R.id.editor);
        activity.findViewById(R.id.fit_button).performClick();
        shadowOf(Looper.getMainLooper()).idleFor(java.time.Duration.ofSeconds(1));
        editor.setDim(0.3f);
        idle();
        assertTrue(editor.leavesGaps());
        assertEquals(activity.getString(R.string.tool_fill),
                ((MaterialButton) activity.findViewById(R.id.fit_button)).getText().toString());
        assertTrue(activity.findViewById(R.id.background_black).isEnabled());
        screenshot(activity.getWindow().getDecorView(), "3-fitted");

        activity.findViewById(R.id.apply_button).performClick();
        idle();
        Dialog sheet = ShadowDialog.getLatestDialog();
        assertTrue(sheet.isShowing());
        screenshot(sheet.getWindow().getDecorView(), "4-apply-sheet");
    }

    @Test
    @Config(qualifiers = "+night")
    public void darkTheme() throws IOException {
        MainActivity activity = Robolectric.buildActivity(MainActivity.class).setup().get();
        activity.showPhoto(Uri.parse("content://test/photo"),
                WallpaperEditorView.Photo.from(landscape()), null);
        idle();
        screenshot(activity.getWindow().getDecorView(), "5-dark");
    }

    private static void idle() {
        shadowOf(Looper.getMainLooper()).idle();
    }

    /** A made-up landscape scene: sky gradient, sun and mountains. */
    private static Bitmap landscape() {
        Bitmap bitmap = Bitmap.createBitmap(1600, 1000, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(bitmap);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setShader(new LinearGradient(0, 0, 0, 1000,
                Color.rgb(255, 140, 90), Color.rgb(70, 60, 160), Shader.TileMode.CLAMP));
        canvas.drawRect(0, 0, 1600, 1000, paint);
        paint.setShader(null);
        paint.setColor(Color.rgb(255, 230, 150));
        canvas.drawCircle(1100, 420, 120, paint);
        Path mountains = new Path();
        mountains.moveTo(0, 1000);
        mountains.lineTo(300, 550);
        mountains.lineTo(600, 800);
        mountains.lineTo(950, 450);
        mountains.lineTo(1350, 820);
        mountains.lineTo(1600, 600);
        mountains.lineTo(1600, 1000);
        mountains.close();
        paint.setColor(Color.rgb(40, 35, 80));
        canvas.drawPath(mountains, paint);
        return bitmap;
    }

    private static void screenshot(View view, String name) throws IOException {
        Bitmap bitmap = Bitmap.createBitmap(view.getWidth(), view.getHeight(), Bitmap.Config.ARGB_8888);
        view.draw(new Canvas(bitmap));
        File dir = new File("build/screenshots");
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(new File(dir, name + ".png"))) {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
        }
    }
}
