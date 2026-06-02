import { FC, useEffect, useState } from 'react';
import { Card, Input, Spin } from 'antd';
import { RedoOutlined, SearchOutlined } from '@ant-design/icons';
import InfiniteScroll from 'react-infinite-scroll-component';
const { Search } = Input;

import {
  CONTACT_EMAIL,
  DEFAULT_PAGE_SIZE,
} from '@shared/ui/constants/common.constants';
import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import {
  setHasMoreReleases,
  setReleases,
} from '@shared/ui/store/settings/settings.slice';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import useDebouncedCallback from '@shared/ui/hooks/useDebounceCallback.hook';
import usePrevious from '@shared/ui/hooks/usePrevious.hook';

import {
  StyledReleaseDrawerEmpty,
  StyledReleaseDrawerFeedbackButton,
  StyledReleaseDrawerList,
  StyledReleasesDrawer,
  StyledReleasesNotesContainer,
} from '@shared/ui/components/molecules/Drawers/ReleasesNotesDrawer/ReleasesNotesDrawer.styled';
import { getReleases } from '@shared/ui/services/releases.services';

import { ReleasesNotesDrawerProps } from '@shared/ui/components/molecules/Drawers/ReleasesNotesDrawer/ReleasesNotesDrawer.props';

const ReleasesNotesDrawer: FC<ReleasesNotesDrawerProps> = (props) => {
  const dispatch = useAppDispatch();
  const handleError = useHandleError();
  const releases = useAppSelector((store) => store.settings.releases);
  const hasMoreReleases = useAppSelector(
    (store) => store.settings.hasMoreReleases,
  );
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchText, setSearchText] = useState('');
  const prevSearchText = usePrevious(searchText);

  useEffect(() => {
    if (prevSearchText !== null && searchText !== prevSearchText) {
      onDebouncedSearch();
    }
  }, [searchText]);

  const onLoadMore = async (isSearch = false) => {
    try {
      if (loading) {
        return;
      }
      setLoading(true);
      const nextPage = isSearch ? 1 : currentPage + 1;
      const { docs = [], hasNextPage = false } = await getReleases({
        page: nextPage,
        limit: DEFAULT_PAGE_SIZE,
        search: searchText,
      });
      dispatch(setHasMoreReleases(hasNextPage));
      dispatch(
        setReleases([
          ...(!isSearch || currentPage > 1 ? releases : []),
          ...docs,
        ]),
      );
      setCurrentPage(nextPage);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  };

  const onDebouncedSearch = useDebouncedCallback(() => {
    setCurrentPage(1);
    onLoadMore(true);
  }, 500);

  return (
    <StyledReleasesDrawer {...props} placement='right' title='Releases notes'>
      <Search
        placeholder='Search releases by title...'
        onChange={(value) => setSearchText(value?.target?.value)}
      />

      {releases.length ? (
        <StyledReleasesNotesContainer id='releases-wrapper'>
          <InfiniteScroll
            dataLength={releases.length}
            next={onLoadMore}
            hasMore={hasMoreReleases}
            loader={
              <div style={{ textAlign: 'center' }}>
                <Spin indicator={<RedoOutlined spin />} size='small' />
              </div>
            }
            scrollableTarget='releases-wrapper'
          >
            {releases.map(({ title, date, changes = [] }) => (
              <Card
                title={title}
                key={date}
                actions={[
                  <StyledReleaseDrawerFeedbackButton
                    key='feedback'
                    type='link'
                    href={`https://mail.google.com/mail/u/0/?su=Feedback about release: ${title}&to=${CONTACT_EMAIL}&tf=cm`}
                    target='_blank'
                  >
                    Send feedback
                  </StyledReleaseDrawerFeedbackButton>,
                ]}
                extra={date}
              >
                <StyledReleaseDrawerList>
                  {changes.map((text, i) => (
                    <li key={i}>{text}</li>
                  ))}
                </StyledReleaseDrawerList>
              </Card>
            ))}
          </InfiniteScroll>
        </StyledReleasesNotesContainer>
      ) : (
        <StyledReleaseDrawerEmpty
          description='No releases were found'
          image={<SearchOutlined />}
        />
      )}
    </StyledReleasesDrawer>
  );
};

export default ReleasesNotesDrawer;
