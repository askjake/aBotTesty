import Document, {
  Html,
  Main,
  NextScript,
  Head,
  DocumentContext,
  DocumentInitialProps,
} from 'next/document';
import { ServerStyleSheet } from 'styled-components';
import { JSX } from 'react';
import { createCache, extractStyle, StyleProvider } from '@ant-design/cssinjs';
import type { AppType } from 'next/app';

interface MyDocumentInitialProps extends DocumentInitialProps {
  styles: JSX.Element;
}

export default class MyDocument extends Document<MyDocumentInitialProps> {
  static async getInitialProps(
    ctx: DocumentContext,
  ): Promise<MyDocumentInitialProps> {
    const sheet = new ServerStyleSheet();
    const cache = createCache();
    const originalRenderPage = ctx.renderPage;

    try {
      ctx.renderPage = () =>
        originalRenderPage({
          enhanceApp: (App: AppType) => (props) =>
            sheet.collectStyles(
              <StyleProvider cache={cache}>
                <App {...props} />
              </StyleProvider>,
            ),
        });

      const initialProps = await Document.getInitialProps(ctx);
      const antdStyle = extractStyle(cache, true);

      return {
        ...initialProps,
        styles: (
          <>
            {initialProps.styles}
            {sheet.getStyleElement()}
            {antdStyle && (
              <style
                data-type='antd-cssinjs'
                dangerouslySetInnerHTML={{ __html: antdStyle }}
              />
            )}
          </>
        ),
      };
    } catch (error) {
      console.error('Error in getInitialProps:', error);
      const initialProps = await Document.getInitialProps(ctx);
      return {
        ...initialProps,
        styles: <>{initialProps.styles}</>,
      };
    } finally {
      sheet.seal();
    }
  }

  render(): JSX.Element {
    return (
      <Html lang='en'>
        <Head />
        <body>
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}
