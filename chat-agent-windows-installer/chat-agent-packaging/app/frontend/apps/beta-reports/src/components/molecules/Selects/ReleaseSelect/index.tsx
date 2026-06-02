import { FC, useCallback, useEffect, useRef, useState } from 'react';
import { Spin } from 'antd';

import { getReportsReleases } from '@/services/beta-reports.services';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { DEFAULT_PAGE_SIZE } from '@shared/ui/constants/common.constants';

import { StyledReleaseSelect } from './ReleaseSelect.styled';

import { ReleaseSelectProps } from './ReleaseSelect.props';
import { SelectOption } from '@shared/ui/types/common.types';

const ReleaseSelect: FC<ReleaseSelectProps> = ({
  className = '',
  platform,
  onOptionsLoaded,
  ...props
}) => {
  const handleError = useHandleError();
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [page, setPage] = useState(1);
  const [options, setOptions] = useState<SelectOption<number>[]>([]);

  const containerRef = useRef<HTMLDivElement>(null);

  const loadOptions = useCallback(
    async (pageNum: number) => {
      if (loading) return;

      setLoading(true);
      try {
        const { docs, hasNextPage } = await getReportsReleases({
          page: pageNum,
          limit: DEFAULT_PAGE_SIZE,
          platform,
        });

        const newOptions = docs.map((item) => ({
          label: item.release,
          value: item.id,
        }));

        if (pageNum === 1) {
          setOptions(newOptions);
          if (onOptionsLoaded && newOptions.length > 0) {
            onOptionsLoaded(newOptions[0].value);
          }
        } else {
          setOptions((prev) => [
            ...prev,
            ...docs.map((item) => ({
              label: item.release,
              value: item.id,
            })),
          ]);
        }

        setHasMore(hasNextPage);
        setPage(pageNum);
      } catch (e) {
        handleError(e);
      } finally {
        setLoading(false);
      }
    },
    [platform, handleError],
  );

  useEffect(() => {
    setOptions([]);
    setPage(1);
    setHasMore(true);
    loadOptions(1);
  }, [platform]);

  const handlePopupScroll = useCallback(
    (e: React.UIEvent<HTMLDivElement>) => {
      const target = e.target as HTMLDivElement;
      const { scrollTop, scrollHeight, clientHeight } = target;

      if (
        scrollTop + clientHeight >= scrollHeight - 10 &&
        hasMore &&
        !loading
      ) {
        loadOptions(page + 1);
      }
    },
    [hasMore, loading, page, loadOptions],
  );

  return (
    <StyledReleaseSelect
      className={`release-select ${className}`}
      loading={loading}
      options={options}
      onPopupScroll={handlePopupScroll}
      notFoundContent={loading ? <Spin size='small' /> : 'No data'}
      showSearch
      allowClear
      placeholder='Select release'
      filterOption={(input, option) =>
        ((option?.label as string) ?? '')
          .toLowerCase()
          .includes(input.toLowerCase())
      }
      popupRender={(menu) => (
        <div ref={containerRef}>
          {menu}
          {loading && hasMore && (
            <div style={{ textAlign: 'center', padding: '8px' }}>
              <Spin size='small' />
            </div>
          )}
        </div>
      )}
      {...props}
    />
  );
};

export default ReleaseSelect;
