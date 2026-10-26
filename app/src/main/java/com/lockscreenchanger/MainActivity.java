package com.lockscreenchanger;

import android.annotation.SuppressLint;
import android.app.WallpaperManager;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.ImageDecoder;
import android.graphics.Matrix;
import android.graphics.Point;
import android.graphics.Rect;
import android.media.ExifInterface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.DisplayMetrics;
import android.view.View;
import android.widget.ImageView;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.PickVisualMediaRequest;
import androidx.activity.result.contract.ActivityResultContracts.PickVisualMedia;
import androidx.annotation.Nullable;
import androidx.annotation.StringRes;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.os.BundleCompat;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.google.android.material.appbar.MaterialToolbar;
import com.google.android.material.bottomsheet.BottomSheetDialog;
import com.google.android.material.button.MaterialButton;
import com.google.android.material.button.MaterialButtonToggleGroup;
import com.google.android.material.color.DynamicColors;
import com.google.android.material.dialog.MaterialAlertDialogBuilder;
import com.google.android.material.slider.Slider;
import com.google.android.material.snackbar.Snackbar;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends AppCompatActivity {

    /** Long side the photo is decoded to: enough detail to zoom in, small enough to draw. */
    private static final int MAX_DECODE_SIDE = 4096;
    private static final String KEY_PHOTO_URI = "photoUri";
    private static final String KEY_EDITOR_STATE = "editorState";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    private ActivityResultLauncher<PickVisualMediaRequest> photoPicker;

    private View root;
    private View controls;
    private WallpaperEditorView editor;
    private View clockOverlay;
    private View emptyState;
    private View progress;
    private MaterialButton rotateButton;
    private MaterialButton fitButton;
    private MaterialButton clockButton;
    private MaterialButton resetButton;
    private MaterialButton photoButton;
    private MaterialButton applyButton;
    private Slider dimSlider;
    private MaterialButtonToggleGroup backgroundGroup;

    private Uri photoUri;
    private boolean wallpaperAllowed;
    private boolean busy;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        EdgeToEdge.enable(this);
        super.onCreate(savedInstanceState);
        DynamicColors.applyToActivityIfAvailable(this);
        setContentView(R.layout.activity_main);

        root = findViewById(R.id.root);
        controls = findViewById(R.id.controls);
        editor = findViewById(R.id.editor);
        clockOverlay = findViewById(R.id.clock_overlay);
        emptyState = findViewById(R.id.empty_state);
        progress = findViewById(R.id.progress);
        rotateButton = findViewById(R.id.rotate_button);
        fitButton = findViewById(R.id.fit_button);
        clockButton = findViewById(R.id.clock_button);
        resetButton = findViewById(R.id.reset_button);
        photoButton = findViewById(R.id.photo_button);
        applyButton = findViewById(R.id.apply_button);
        dimSlider = findViewById(R.id.dim_slider);
        backgroundGroup = findViewById(R.id.background_group);

        applyWindowInsets();

        Point screen = screenSize();
        float screenAspect = (float) screen.x / screen.y;
        PhoneFrameLayout phoneFrame = findViewById(R.id.phone_frame);
        phoneFrame.setAspectRatio(screenAspect);
        editor.setFrameAspect(screenAspect);

        photoPicker = registerForActivityResult(new PickVisualMedia(), uri -> {
            if (uri != null) {
                loadPhoto(uri, null);
            }
        });

        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        toolbar.setOnMenuItemClickListener(item -> {
            if (item.getItemId() == R.id.action_remove_lock_photo) {
                confirmRemoveLockPhoto();
                return true;
            } else if (item.getItemId() == R.id.action_keyboard_help) {
                new MaterialAlertDialogBuilder(this)
                        .setTitle(R.string.keyboard_help_title)
                        .setMessage(R.string.keyboard_help_message)
                        .setPositiveButton(android.R.string.ok, null)
                        .show();
                return true;
            }
            return false;
        });

        emptyState.setOnClickListener(v -> pickPhoto());
        photoButton.setOnClickListener(v -> pickPhoto());
        rotateButton.setOnClickListener(v -> editor.rotate());
        fitButton.setOnClickListener(v -> editor.toggleFit());
        resetButton.setOnClickListener(v -> editor.reset());
        clockButton.addOnCheckedChangeListener((button, checked) -> updateControls());
        applyButton.setOnClickListener(v -> showApplySheet());
        dimSlider.setLabelFormatter(value -> Math.round(value) + "%");
        dimSlider.addOnChangeListener((slider, value, fromUser) -> {
            if (fromUser) {
                editor.setDim(value / 100f);
            }
        });
        backgroundGroup.addOnButtonCheckedListener((group, id, checked) -> {
            if (checked) {
                editor.setBackgroundMode(id == R.id.background_black ? WallpaperEditorView.BACKGROUND_BLACK
                        : id == R.id.background_white ? WallpaperEditorView.BACKGROUND_WHITE
                        : WallpaperEditorView.BACKGROUND_BLUR);
            }
        });
        editor.setOnChangeListener(this::updateControls);

        WallpaperManager wallpaperManager = WallpaperManager.getInstance(this);
        wallpaperAllowed = wallpaperManager.isWallpaperSupported()
                && wallpaperManager.isSetWallpaperAllowed();
        if (!wallpaperAllowed) {
            showBlockedState();
        }
        toolbar.getMenu().findItem(R.id.action_remove_lock_photo).setEnabled(wallpaperAllowed);

        if (savedInstanceState == null) {
            // Not set in XML: MaterialButton ignores android:checked there.
            clockButton.setChecked(true);
        } else {
            Uri savedUri = BundleCompat.getParcelable(savedInstanceState, KEY_PHOTO_URI, Uri.class);
            if (savedUri != null) {
                loadPhoto(savedUri, savedInstanceState.getBundle(KEY_EDITOR_STATE));
            }
        }
        updateControls();
    }

    @Override
    protected void onSaveInstanceState(Bundle outState) {
        super.onSaveInstanceState(outState);
        if (photoUri != null && editor.hasPhoto()) {
            outState.putParcelable(KEY_PHOTO_URI, photoUri);
            outState.putBundle(KEY_EDITOR_STATE, editor.saveState());
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        // Let a wallpaper change that's already running finish; results are dropped once destroyed.
        executor.shutdown();
    }

    /** Draws behind the system bars, padding the content so nothing ends up underneath them. */
    private void applyWindowInsets() {
        View content = findViewById(R.id.content);
        int controlsBottomPadding = controls.getPaddingBottom();
        ViewCompat.setOnApplyWindowInsetsListener(root, (view, windowInsets) -> {
            Insets insets = windowInsets.getInsets(WindowInsetsCompat.Type.systemBars()
                    | WindowInsetsCompat.Type.displayCutout());
            content.setPadding(insets.left, insets.top, insets.right, 0);
            // The controls panel's background runs under the navigation bar.
            controls.setPadding(controls.getPaddingLeft(), controls.getPaddingTop(),
                    controls.getPaddingRight(), controlsBottomPadding + insets.bottom);
            return WindowInsetsCompat.CONSUMED;
        });
    }

    private void showBlockedState() {
        ImageView icon = findViewById(R.id.empty_icon);
        icon.setImageResource(R.drawable.ic_lock);
        TextView title = findViewById(R.id.empty_title);
        title.setText(R.string.blocked_title);
        TextView message = findViewById(R.id.empty_message);
        message.setText(R.string.status_blocked);
        emptyState.setClickable(false);
    }

    private void pickPhoto() {
        photoPicker.launch(new PickVisualMediaRequest.Builder()
                .setMediaType(PickVisualMedia.ImageOnly.INSTANCE)
                .build());
    }

    private void loadPhoto(Uri uri, @Nullable Bundle editorState) {
        setBusy(true);
        executor.execute(() -> {
            WallpaperEditorView.Photo photo = null;
            String error = null;
            try {
                photo = WallpaperEditorView.Photo.from(decodeImage(uri));
            } catch (Exception | OutOfMemoryError e) {
                error = String.valueOf(e.getMessage());
            }
            WallpaperEditorView.Photo loaded = photo;
            String loadError = error;
            mainHandler.post(() -> {
                if (isDestroyed()) {
                    return;
                }
                setBusy(false);
                if (loaded != null) {
                    showPhoto(uri, loaded, editorState);
                } else if (editorState == null) {
                    // Only report errors for photos the user just picked, not silent restores.
                    showError(R.string.load_error_title, getString(R.string.status_error, loadError));
                }
            });
        });
    }

    /** Puts a decoded photo in the editor, restoring earlier adjustments if there are any. */
    void showPhoto(Uri uri, WallpaperEditorView.Photo photo, @Nullable Bundle editorState) {
        photoUri = uri;
        editor.setPhoto(photo, editorState);
        updateControls();
    }

    private void setBusy(boolean busy) {
        this.busy = busy;
        updateControls();
    }

    /** Brings every control in line with the editor and whether a photo or a task is in progress. */
    private void updateControls() {
        boolean hasPhoto = editor.hasPhoto();
        boolean editable = hasPhoto && !busy && wallpaperAllowed;

        emptyState.setVisibility(hasPhoto || busy ? View.GONE : View.VISIBLE);
        progress.setVisibility(busy ? View.VISIBLE : View.GONE);
        clockOverlay.setVisibility(hasPhoto && clockButton.isChecked() ? View.VISIBLE : View.GONE);
        editor.setEnabled(editable);

        rotateButton.setEnabled(editable);
        fitButton.setEnabled(editable && editor.canFit());
        fitButton.setText(editor.leavesGaps() ? R.string.tool_fill : R.string.tool_fit);
        clockButton.setEnabled(hasPhoto);
        resetButton.setEnabled(editable);

        dimSlider.setEnabled(editable);
        float dimPercent = Math.round(editor.getDim() * 100f);
        if (dimSlider.getValue() != dimPercent) {
            dimSlider.setValue(dimPercent);
        }

        int backgroundId;
        switch (editor.getBackgroundMode()) {
            case WallpaperEditorView.BACKGROUND_BLACK:
                backgroundId = R.id.background_black;
                break;
            case WallpaperEditorView.BACKGROUND_WHITE:
                backgroundId = R.id.background_white;
                break;
            default:
                backgroundId = R.id.background_blur;
                break;
        }
        if (backgroundGroup.getCheckedButtonId() != backgroundId) {
            backgroundGroup.check(backgroundId);
        }
        // The background only shows when the photo doesn't cover the whole screen.
        boolean backgroundVisible = editable && editor.leavesGaps();
        for (int i = 0; i < backgroundGroup.getChildCount(); i++) {
            backgroundGroup.getChildAt(i).setEnabled(backgroundVisible);
        }

        photoButton.setEnabled(wallpaperAllowed && !busy);
        photoButton.setText(hasPhoto ? R.string.change_photo : R.string.choose_photo);
        applyButton.setEnabled(editable);
    }

    @SuppressLint("InflateParams") // A bottom sheet's content has no parent to inflate into.
    private void showApplySheet() {
        BottomSheetDialog sheet = new BottomSheetDialog(this);
        View content = getLayoutInflater().inflate(R.layout.sheet_apply, null);
        content.findViewById(R.id.option_lock).setOnClickListener(v -> {
            sheet.dismiss();
            applyWallpaper(WallpaperManager.FLAG_LOCK, R.string.done_lock);
        });
        content.findViewById(R.id.option_home).setOnClickListener(v -> {
            sheet.dismiss();
            applyWallpaper(WallpaperManager.FLAG_SYSTEM, R.string.done_home);
        });
        content.findViewById(R.id.option_both).setOnClickListener(v -> {
            sheet.dismiss();
            applyWallpaper(WallpaperManager.FLAG_SYSTEM | WallpaperManager.FLAG_LOCK,
                    R.string.done_both);
        });
        // Wallpaper-based system colors arrived in Android 12.
        content.findViewById(R.id.colors_note).setVisibility(
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.S ? View.VISIBLE : View.GONE);
        sheet.setContentView(content);
        sheet.show();
    }

    private void applyWallpaper(int which, @StringRes int doneMessage) {
        WallpaperEditorView.Renderer renderer = editor.snapshot();
        Point size = screenSize();
        runWallpaperTask(doneMessage, () -> {
            Bitmap wallpaper = renderer.render(size.x, size.y);
            return WallpaperManager.getInstance(this).setBitmap(wallpaper, null, true, which) != 0;
        });
    }

    private void confirmRemoveLockPhoto() {
        new MaterialAlertDialogBuilder(this)
                .setTitle(R.string.remove_lock_photo)
                .setMessage(R.string.remove_lock_photo_message)
                .setNegativeButton(android.R.string.cancel, null)
                .setPositiveButton(R.string.remove, (dialog, which) ->
                        runWallpaperTask(R.string.done_cleared, () -> {
                            WallpaperManager.getInstance(this).clear(WallpaperManager.FLAG_LOCK);
                            return true;
                        }))
                .show();
    }

    private interface WallpaperTask {
        /** Returns false if the system refused the change. */
        boolean run() throws Exception;
    }

    /** Runs {@code task} off the UI thread, then reports success or what went wrong. */
    private void runWallpaperTask(@StringRes int doneMessage, WallpaperTask task) {
        setBusy(true);
        executor.execute(() -> {
            String error = null;
            try {
                if (!task.run()) {
                    error = getString(R.string.status_refused);
                }
            } catch (SecurityException e) {
                error = getString(R.string.status_blocked);
            } catch (Exception | OutOfMemoryError e) {
                error = getString(R.string.status_error, String.valueOf(e.getMessage()));
            }
            String result = error;
            mainHandler.post(() -> {
                if (isDestroyed()) {
                    return;
                }
                setBusy(false);
                if (result == null) {
                    Snackbar.make(root, doneMessage, Snackbar.LENGTH_LONG)
                            .setAnchorView(controls)
                            .show();
                } else {
                    showError(R.string.error_title, result);
                }
            });
        });
    }

    private void showError(@StringRes int title, String message) {
        new MaterialAlertDialogBuilder(this)
                .setTitle(title)
                .setMessage(message)
                .setPositiveButton(android.R.string.ok, null)
                .show();
    }

    /** The full screen size in pixels, in portrait. */
    @SuppressWarnings("deprecation") // getRealMetrics is the only option before Android 11.
    private Point screenSize() {
        int width;
        int height;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Rect bounds = getWindowManager().getMaximumWindowMetrics().getBounds();
            width = bounds.width();
            height = bounds.height();
        } else {
            DisplayMetrics metrics = new DisplayMetrics();
            getWindowManager().getDefaultDisplay().getRealMetrics(metrics);
            width = metrics.widthPixels;
            height = metrics.heightPixels;
        }
        if (width <= 0 || height <= 0) {
            // No window bounds yet (as in tests); the app's display metrics are close enough.
            DisplayMetrics metrics = getResources().getDisplayMetrics();
            width = metrics.widthPixels;
            height = metrics.heightPixels;
        }
        return new Point(Math.min(width, height), Math.max(width, height));
    }

    /** Decodes the picked photo upright (EXIF rotation applied) and at most {@link #MAX_DECODE_SIDE}. */
    private Bitmap decodeImage(Uri uri) throws IOException {
        if (Build.VERSION.SDK_INT >= 28) {
            // ImageDecoder applies EXIF rotation itself.
            ImageDecoder.Source source = ImageDecoder.createSource(getContentResolver(), uri);
            return ImageDecoder.decodeBitmap(source, (decoder, info, src) -> {
                decoder.setTargetSampleSize(
                        sampleSize(info.getSize().getWidth(), info.getSize().getHeight()));
                // The wallpaper is rendered on a software canvas, which can't draw hardware bitmaps.
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
        options.inSampleSize = sampleSize(bounds.outWidth, bounds.outHeight);
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

    /** Smallest power-of-two downsample that brings the long side within {@link #MAX_DECODE_SIDE}. */
    private static int sampleSize(int width, int height) {
        int longSide = Math.max(width, height);
        int sample = 1;
        while (longSide / sample > MAX_DECODE_SIDE) {
            sample *= 2;
        }
        return sample;
    }
}
