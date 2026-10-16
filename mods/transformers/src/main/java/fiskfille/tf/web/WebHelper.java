package fiskfille.tf.web;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.List;

/**
 * @author gegy1000
 */
public class WebHelper
{
    private static String pastebinURLPrefix = "http://pastebin.com/raw.php?i=";
    private static final int TIMEOUT_MS = 5000;

    public static List<String> downloadFileList(String urlString) throws MalformedURLException, IOException
    {
        List<String> text = new ArrayList<String>();

        URL url = new URL(urlString);
        // URL.openStream() has no timeouts, so an unreachable host could stall the caller indefinitely
        URLConnection connection = url.openConnection();
        connection.setConnectTimeout(TIMEOUT_MS);
        connection.setReadTimeout(TIMEOUT_MS);
        BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));

        String currentLine;

        while ((currentLine = reader.readLine()) != null)
        {
            text.add(currentLine);
        }

        reader.close();

        return text;
    }

    public static String downloadFile(String urlString) throws MalformedURLException, IOException
    {
        String text = "";

        List<String> lines = downloadFileList(urlString);

        for (String string : lines)
        {
            text += string + "\r\n";
        }

        return text;
    }

    public static List<String> readPastebinAsList(String pastebinFileName) throws MalformedURLException, IOException
    {
        return WebHelper.downloadFileList(pastebinURLPrefix + pastebinFileName);
    }

    public static String readPastebin(String pastebinFileName) throws MalformedURLException, IOException
    {
        return WebHelper.downloadFile(pastebinURLPrefix + pastebinFileName);
    }
}
