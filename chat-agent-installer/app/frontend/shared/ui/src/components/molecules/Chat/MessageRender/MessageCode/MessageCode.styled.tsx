import styled from 'styled-components';
import { CodeHighlighter } from '@ant-design/x';

export const StyledCodeHighlighter = styled(CodeHighlighter)`
  & .ant-codeHighlighter-code {
    background: rgba(150, 150, 150, 0.1) !important;
    border: none;
  }

  & .ant-codeHighlighter-code pre,
  & .ant-codeHighlighter-code code {
    background: transparent !important;
  }
  & .ant-codeHighlighter-code code span:not([class]) {
    color: ${({ theme }) => theme?.colors?.text || '#0d0d0d'};
  }

  & .ant-codeHighlighter-code code span[style*='color: rgb(56, 58, 66)'] {
    color: ${({ theme }) => theme?.colors?.codeText || '#24292e'} !important;
  }
`;
