import { Think } from '@ant-design/x';
import { memo, useMemo, useState } from 'react';
import { type ComponentProps } from '@ant-design/x-markdown';

const MessageThinking = memo(
  (props: ComponentProps & { loading: boolean }) => {
    const [expand, setExpand] = useState(false);
    const isLoading = useMemo(() => props.loading, [props.loading]);
    const title = useMemo(
      () => (isLoading ? 'Thinking...' : 'Show reasoning'),
      [isLoading],
    );

    return (
      <Think
        title={title}
        loading={isLoading}
        expanded={expand}
        onClick={() => setExpand(!expand)}
        blink={isLoading}
      >
        {props.children}
      </Think>
    );
  },
  (oldProps, newProps) =>
    oldProps.loading === newProps.loading &&
    oldProps.children === newProps.children,
);
export default MessageThinking;
