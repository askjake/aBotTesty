import { memo } from 'react';
import { Flex, Image } from 'antd';
import { FileCard } from '@ant-design/x';

import { StyledFileBubbleImage } from '@shared/ui/components/molecules/Chat/Bubbles/FileBubble/FileBubble.styled';
import CustomBubble from '@shared/ui/components/atoms/Bubbles/CustomBubble';

const FileBubble = memo(({ bubble }: { bubble: any }) => {
  return (
    <CustomBubble
      role='fileUser'
      placement='end'
      variant='borderless'
      content=''
      contentRender={() => {
        return (
          <Flex wrap justify='end' gap='middle'>
            {(bubble.content as any[]).map((item) =>
              item?.thumbUrl ? (
                <Image.PreviewGroup key={item.uid}>
                  <StyledFileBubbleImage src={`/api/image-proxy/${item.uid}`} />
                </Image.PreviewGroup>
              ) : (
                <FileCard key={item.uid} name={item.name} src={item.url} />
              ),
            )}
          </Flex>
        );
      }}
    />
  );
});

export default FileBubble;
