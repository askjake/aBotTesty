import { FC, useEffect, useRef } from 'react';
import { Input, Spin } from 'antd';
import { CommentOutlined, RedoOutlined } from '@ant-design/icons';
import InfiniteScroll from 'react-infinite-scroll-component';
import { Conversations } from '@ant-design/x';

import { StyledSearchModal } from '@/components/molecules/Modals/SearchModal/SearchModal.styled';
import EmptyChats from '@/components/molecules/Empty/EmptyChats';

import { groupable } from '@shared/ui/utils/messages.utils';

import { SearchModalProps } from '@/components/molecules/Modals/SearchModal/SearchModal.props';

const SearchModal: FC<SearchModalProps> = ({
  onSearchChange,
  items = [],
  onLoadMore,
  customSearchPlaceholder = 'Search items...',
  customItemIcon = <CommentOutlined />,
  hasMoreData = false,
  activeKey,
  onActiveKeyChange = () => {},
  menuConfig,
  ...props
}) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkAndLoadMore = () => {
      const container = scrollContainerRef.current;
      const menu = menuRef.current;

      if (!container || !menu || !hasMoreData || !props.open) {
        return;
      }

      const containerHeight = container.clientHeight;
      const menuHeight = menu.scrollHeight || menu.clientHeight;
      const freeSpace = containerHeight - menuHeight;
      const freeSpacePercentage = (freeSpace / containerHeight) * 100;
      if (freeSpacePercentage > 0) {
        onLoadMore(false);
      }
    };

    let timeoutId: NodeJS.Timeout;
    const handleResize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => {
        checkAndLoadMore();
      }, 150);
    };

    const initTimer = setTimeout(() => {
      checkAndLoadMore();
    }, 100);

    window.addEventListener('resize', handleResize);

    return () => {
      clearTimeout(initTimer);
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
    };
  }, [hasMoreData]);

  return (
    <StyledSearchModal
      title={
        <Input
          placeholder={customSearchPlaceholder}
          onChange={(e) => onSearchChange(e?.target?.value)}
          variant='borderless'
        />
      }
      footer={null}
      destroyOnHidden
      {...props}
    >
      {!items.length ? (
        <EmptyChats />
      ) : (
        <div ref={scrollContainerRef}>
          <InfiniteScroll
            dataLength={items.length}
            next={onLoadMore}
            hasMore={hasMoreData}
            height='50vh'
            loader={
              <div style={{ textAlign: 'center' }}>
                <Spin indicator={<RedoOutlined spin />} size='small' />
              </div>
            }
          >
            <div ref={menuRef}>
              <Conversations
                activeKey={activeKey}
                items={items}
                groupable={groupable(customItemIcon)}
                menu={menuConfig}
                onActiveChange={(key: string) => onActiveKeyChange(key)}
              />
            </div>
          </InfiniteScroll>
        </div>
      )}
    </StyledSearchModal>
  );
};

export default SearchModal;
