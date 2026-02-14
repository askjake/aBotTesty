import AppsTemplate from '@/components/templates/AppsTemplate';
import Head from 'next/head';
import { GetServerSideProps, GetServerSidePropsResult } from 'next';
import { TemplateErrorProps } from '@shared/ui/interfaces/templates.interfaces';
import { wrapper } from '@shared/ui/store';
import { fetchUserData } from '@/utils/requests.utils';
import {
  setHasMoreReleases,
  setReleases,
  setShowReleaseModal,
  setUser,
} from '@shared/ui/store/settings/settings.slice';
import {
  setVaultMode,
  setVaultModeRegistered,
} from '@shared/ui/store/chats/chats.slice';
import customDayjs from '@shared/ui/libs/dayjs.libs';
import { updateLastReleaseDate } from '@shared/ui/services/releases.services';
import { handleServerError } from '@shared/ui/utils/errors.utils';

const AppsPage = () => {
  return (
    <>
      <Head>
        <title>Dish chat - Apps</title>
        <meta name='viewport' content='width=device-width, initial-scale=1' />
        <link rel='icon' href='/favicon.ico' />
      </Head>
      <AppsTemplate />;
    </>
  );
};

export const getServerSideProps: GetServerSideProps<TemplateErrorProps> =
  wrapper.getServerSideProps(
    (store) =>
      async (ctx): Promise<GetServerSidePropsResult<TemplateErrorProps>> => {
        try {
          // Check if auth is disabled
          const disableAuth = process.env.NEXT_PUBLIC_DISABLE_AUTH === 'true';
          
          let userEmail = 
            ctx?.req?.cookies['userEmail'] ||
            ctx?.req?.headers['x-auth-request-email'];

          // If auth is disabled and no email, use a default test user
          if (disableAuth && !userEmail) {
            userEmail = 'test-user@dish.com';
            console.log('[NO-AUTH MODE] Using default test user:', userEmail);
          }

          if (!userEmail) {
            return {
              redirect: {
                destination: '/403',
                permanent: false,
              },
            };
          }
          
          const incomingHeaders = {
            ...ctx.req.headers,
            'X-Auth-Request-Email': userEmail,
          };
          // Fetch user data and vault settings
          const { user, isVaultModeRegistered, isVaultModeEnabled, releases } =
            await fetchUserData(incomingHeaders);

          const releasesList = releases?.docs || [];

          // Dispatch user and vault data
          store.dispatch(setUser(user));
          store.dispatch(setVaultModeRegistered(isVaultModeRegistered));
          store.dispatch(setVaultMode(isVaultModeEnabled));
          store.dispatch(setReleases(releasesList));
          store.dispatch(setHasMoreReleases(!!releases?.hasNextPage));
          const lastRelease = releasesList[0];
          if (lastRelease) {
            const lastReleaseDate = user?.last_release_date;
            if (
              !lastReleaseDate ||
              customDayjs(lastRelease.date).isAfter(
                customDayjs(lastReleaseDate),
                'day',
              )
            ) {
              await updateLastReleaseDate({
                date: customDayjs(lastRelease.date).toDate(),
                incomingHeaders,
              });
              store.dispatch(setShowReleaseModal(true));
              store.dispatch(
                setUser({
                  ...user,
                  last_release_date: lastRelease.date,
                }),
              );
            }
          }

          return {
            props: {},
          };
        } catch (error: any) {
          return handleServerError({
            error,
            ctx,
          });
        }
      },
  );

export default AppsPage;
