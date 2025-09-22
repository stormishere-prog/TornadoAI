package com.tornadoai;

import android.annotation.SuppressLint;
import android.graphics.Bitmap;
import android.net.http.SslError;
import android.os.Bundle;
import android.webkit.*;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.google.android.material.appbar.MaterialToolbar;

public class MainActivity extends AppCompatActivity {
    private static final String START_URL = "http://127.0.0.1:8787/ui_tabs.html"; // or "/"
    private WebView web;
    private SwipeRefreshLayout swipe;

    @SuppressLint("SetJavaScriptEnabled")
    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        MaterialToolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);

        swipe = findViewById(R.id.swipe);
        web = findViewById(R.id.web);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setDisplayZoomControls(false);

        web.setWebViewClient(new WebViewClient() {
            @Override public void onPageStarted(WebView view, String url, Bitmap favicon) {
                swipe.setRefreshing(true);
            }
            @Override public void onPageFinished(WebView view, String url) {
                swipe.setRefreshing(false);
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest req, WebResourceError err) {
                swipe.setRefreshing(false);
                Toast.makeText(MainActivity.this, getString(R.string.server_down), Toast.LENGTH_SHORT).show();
            }
            @Override public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.proceed(); // local only
            }
        });

        swipe.setOnRefreshListener(() -> web.reload());

        // If server isn’t up yet, first load will show toast; pull-to-refresh once Termux server is running.
        web.loadUrl(START_URL);
    }

    @Override public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
