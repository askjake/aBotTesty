import { createGlobalStyle } from 'styled-components';

const GlobalStyles = createGlobalStyle`
  * {
      padding: 0;
      margin: 0;
      scrollbar-color: ${({ theme }) => theme?.colors?.primary || '#fc1c39'} transparent;
      scrollbar-width: thin;
  }  
  
  html, body {
    min-height: 100vh;
    font-size: 16px;
    color: ${({ theme }) => theme?.colors?.text || '#0d0d0d'};
  }
  
  .markdown-it-code-copy {
      width: 15px;
      height: 15px;
      border: none;
      outline: none;
      background: transparent;
      top: 15px !important;
      right: 15px !important;
      
      span {
          color: ${({ theme }) => theme?.colors?.primary || '#fc1c39'};
      }
  }
  
  .ant-conversations-item {
    padding-left: 1.8rem !important;
  }
  
`;

export default GlobalStyles;
