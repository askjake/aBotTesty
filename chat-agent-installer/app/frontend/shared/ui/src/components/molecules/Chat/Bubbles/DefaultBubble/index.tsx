import { memo } from 'react';

import CustomBubble from '@shared/ui/components/atoms/Bubbles/CustomBubble';

const DefaultBubble = memo(({ bubble }: { bubble: any }) => {
  return (
    <CustomBubble
      content={bubble.content}
      variant={bubble?.variant || 'borderless'}
    />
  );
});

export default DefaultBubble;
