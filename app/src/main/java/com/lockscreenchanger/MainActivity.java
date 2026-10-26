package com.lockscreenchanger;

import android.app.Activity;
import android.app.WallpaperManager;
import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageDecoder;
import android.graphics.Matrix;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.TextView;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    private static final int REQUEST_PICK_IMAGE = 1;

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private ImageView preview;
    private TextView status;
    private Button pickButton;
    private Button setLockButton;
    private Button setBothButton;
    private Button clearLockButton;

    private Bitmap selectedImage;
    private boolean wallpaperAllowed;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        preview = findViewById(R.id.preview);
        status = findViewById(R.id.status);
        pickButton = findViewById(R.id.pick_button);
        setLockButton = findViewById(R.id.set_lock_button);
        setBothButton = findViewById(R.id.set_both_button);
        clearLockButton = findViewById(R.id.clear_lock_button);

        pickButton.setOnClickListener(v -> pickImage());
        setLockButton.setOnClickListener(v -> applyWallpaper(WallpaperManager.FLAG_LOCK));
        setBothButton.setOnClickListener(
                v -> applyWallpaper(WallpaperManager.FLAG_LOCK | WallpaperManager.FLAG_SYSTEM));
        clearLockButton.setOnClickListener(v -> clearLockWallpaper());

        WallpaperManager wallpaperManager = WallpaperManager.getInstance(this);
        wallpaperAllowed = wallpaperManager.isWallpaperSupported()
                && wallpaperManager.isSetWallpaperAllowed();
        if (wallpaperAllowed) {
            status.setText(R.string.status_ready);
        } else {
            status.setText(R.string.status_blocked);
        }
        updateButtons(false);
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        executor.shutdownNow();
    }

    private void pickImage() {
        Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
        intent.setType("image/*");
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        startActivityForResult(Intent.createChooser(intent, getString(R.string.pick_photo)),
                REQUEST_PICK_IMAGE);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQUEST_PICK_IMAGE || resultCode != RESULT_OK
                || data == null || data.getData() == null) {
            return;
        }
        Uri uri = data.getData();
        runInBackground(getString(R.string.status_loading), () -> {
            Bitmap bitmap = decodeImage(uri);
            mainHandler.post(() -> {
                if (isDestroyed()) {
                    return;
                }
                selectedImage = bitmap;
                preview.setImageBitmap(bitmap);
                preview.setVisibility(View.VISIBLE);
            });
            return getString(R.string.status_loaded);
        });
    }

    private void applyWallpaper(int which) {
        Bitmap bitmap = selectedImage;
        if (bitmap == null) {
            return;
        }
        runInBackground(getString(R.string.status_setting), () -> {
            int id = WallpaperManager.getInstance(this).setBitmap(bitmap, null, true, which);
            return getString(id != 0 ? R.string.status_done : R.string.status_refused);
        });
    }

    private void clearLockWallpaper() {
        runInBackground(getString(R.string.status_setting), () -> {
            WallpaperManager.getInstance(this).clear(WallpaperManager.FLAG_LOCK);
            return getString(R.string.status_cleared);
        });
    }

    private interface Task {
        String run() throws Exception;
    }

    /** Runs {@code task} off the UI thread and shows its returned message (or error) when done. */
    private void runInBackground(String busyMessage, Task task) {
        status.setText(busyMessage);
        updateButtons(true);
        executor.execute(() -> {
            String message;
            try {
                message = task.run();
            } catch (SecurityException e) {
                message = getString(R.string.status_blocked);
            } catch (Exception | OutOfMemoryError e) {
                message = getString(R.string.status_error, String.valueOf(e.getMessage()));
            }
            String result = message;
            mainHandler.post(() -> {
                if (isDestroyed()) {
                    return;
                }
                status.setText(result);
                updateButtons(false);
            });
        });
    }

    private void updateButtons(boolean busy) {
        boolean hasImage = selectedImage != null;
        pickButton.setEnabled(!busy && wallpaperAllowed);
        setLockButton.setEnabled(!busy && wallpaperAllowed && hasImage);
        setBothButton.setEnabled(!busy && wallpaperAllowed && hasImage);
        clearLockButton.setEnabled(!busy && wallpaperAllowed);
    }

    /**
     * Decodes the picked image, downsampled to roughly screen size (full-resolution camera
     * photos can be too large to set as a wallpaper) and rotated upright using its EXIF data.
     */
    private Bitmap decodeImage(Uri uri) throws IOException {
        DisplayMetrics metrics = getResources().getDisplayMetrics();
        int targetSide = Math.max(metrics.widthPixels, metrics.heightPixels);

        if (Build.VERSION.SDK_INT >= 28) {
            // ImageDecoder applies EXIF rotation itself.
            ImageDecoder.Source source = ImageDecoder.createSource(getContentResolver(), uri);
            return ImageDecoder.decodeBitmap(source, (decoder, info, src) -> {
                decoder.setTargetSampleSize(sampleSize(
                        info.getSize().getWidth(), info.getSize().getHeight(), targetSide));
                // Hardware bitmaps can't be written out by WallpaperManager.
                decoder.setAllocator(ImageDecoder.ALLOCATOR_SOFTWARE);
            });
        }

        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            BitmapFactory.decodeStream(in, null, bounds);
        }
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) {
            throw new IOException(getString(R.string.error_not_image));
        }

        BitmapFactory.Options options = new BitmapFactory.Options();
        options.inSampleSize = sampleSize(bounds.outWidth, bounds.outHeight, targetSide);
        Bitmap bitmap;
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            bitmap = BitmapFactory.decodeStream(in, null, options);
        }
        if (bitmap == null) {
            throw new IOException(getString(R.string.error_not_image));
        }

        int orientation;
        try (InputStream in = getContentResolver().openInputStream(uri)) {
            orientation = new ExifInterface(in).getAttributeInt(
                    ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL);
        } catch (IOException e) {
            orientation = ExifInterface.ORIENTATION_NORMAL;
        }
        int degrees;
        switch (orientation) {
            case ExifInterface.ORIENTATION_ROTATE_90:
                degrees = 90;
                break;
            case ExifInterface.ORIENTATION_ROTATE_180:
                degrees = 180;
                break;
            case ExifInterface.ORIENTATION_ROTATE_270:
                degrees = 270;
                break;
            default:
                return bitmap;
        }
        Matrix matrix = new Matrix();
        matrix.postRotate(degrees);
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.getWidth(), bitmap.getHeight(), matrix, true);
    }

    /** Largest power-of-two downsample that keeps the image's long side at least {@code targetSide}. */
    private static int sampleSize(int width, int height, int targetSide) {
        int longSide = Math.max(width, height);
        int sample = 1;
        while (longSide / (sample * 2) >= targetSide) {
            sample *= 2;
        }
        return sample;
    }
}
