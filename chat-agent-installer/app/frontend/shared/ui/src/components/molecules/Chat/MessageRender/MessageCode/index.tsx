import { Mermaid } from '@ant-design/x';
import { type ComponentProps } from '@ant-design/x-markdown';
import { FC } from 'react';

import { StyledCodeHighlighter } from '@shared/ui/components/molecules/Chat/MessageRender/MessageCode/MessageCode.styled';

const MessageCode: FC<ComponentProps> = (props) => {
  const { className, children } = props;
  const lang = className?.match(/language-(\w+)/)?.[1] || '';

  if (typeof children !== 'string') return null;
  if (lang === 'mermaid') {
    return <Mermaid>{children}</Mermaid>;
  }
  return <StyledCodeHighlighter lang={lang}>{children}</StyledCodeHighlighter>;
};

export default MessageCode;
